import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


class CreateSavingsBody(BaseModel):
    anggota_ref: str
    jumlah: float = Field(gt=0)
    jenis: str | None = None


@router.get("/savings", response_model=ApiResponse)
async def list_savings(
    anggota_ref: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "s.koperasi_ref = :ref"
    params: dict = {"ref": ref, "offset": offset, "limit": limit}
    if anggota_ref:
        where += " AND s.anggota_ref = :anggota"
        params["anggota"] = anggota_ref

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM koptumbuh.simpanan_anggota s WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("offset", "limit")},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            f"""SELECT s.simpanan_ref, s.anggota_ref, a.nama, s.periode_pembayaran,
                       s.jumlah_simpanan, s.status, s.dibuat_pada, s.dibayar_pada
                FROM koptumbuh.simpanan_anggota s
                LEFT JOIN koptumbuh.anggota_koperasi a ON a.anggota_ref = s.anggota_ref
                WHERE {where}
                ORDER BY s.dibuat_pada DESC
                OFFSET :offset LIMIT :limit"""
        ),
        params,
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": r[0],
                "anggota_ref": r[1],
                "nama": r[2],
                "periode": r[3],
                "jumlah": float(r[4] or 0),
                "status": r[5],
                "created_at": str(r[6]) if r[6] else None,
                "paid_at": str(r[7]) if r[7] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/savings", response_model=ApiResponse)
async def create_savings(
    body: CreateSavingsBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    exists = (await db.execute(
        text(
            "SELECT 1 FROM koptumbuh.anggota_koperasi "
            "WHERE anggota_ref=:a AND koperasi_ref=:ref"
        ),
        {"a": body.anggota_ref, "ref": ref},
    )).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    sid = f"SIMPAN-{uuid.uuid4().hex[:12].upper()}"
    periode = body.jenis or "Simpanan"
    await db.execute(
        text(
            "INSERT INTO koptumbuh.simpanan_anggota "
            "(simpanan_ref, koperasi_ref, anggota_ref, periode_pembayaran, "
            " jumlah_simpanan, status, dibayar_pada) "
            "VALUES (:id, :ref, :anggota, :periode, :jumlah, 'PAID', NOW())"
        ),
        {
            "id": sid,
            "ref": ref,
            "anggota": body.anggota_ref,
            "periode": periode,
            "jumlah": body.jumlah,
        },
    )
    await db.commit()
    return ApiResponse(data={
        "id": sid,
        "anggota_ref": body.anggota_ref,
        "jumlah": body.jumlah,
        "periode": periode,
        "status": "PAID",
    })
