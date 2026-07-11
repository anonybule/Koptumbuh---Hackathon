import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


class CreateCustomerBody(BaseModel):
    nama_pelanggan: str
    nomor_whatsapp: str | None = None
    anggota_ref: str | None = None


@router.get("/customers", response_model=ApiResponse)
async def list_customers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.pelanggan_koptumbuh "
            "WHERE koperasi_ref=:ref AND status_aktif=true"
        ),
        {"ref": ref},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT pelanggan_id, nama_pelanggan, nomor_whatsapp, anggota_ref, created_at "
            "FROM koptumbuh.pelanggan_koptumbuh "
            "WHERE koperasi_ref=:ref AND status_aktif=true "
            "ORDER BY nama_pelanggan OFFSET :offset LIMIT :limit"
        ),
        {"ref": ref, "offset": offset, "limit": limit},
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "nama_pelanggan": r[1],
                "nomor_whatsapp": r[2],
                "anggota_ref": r[3],
                "created_at": str(r[4]) if r[4] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/customers", response_model=ApiResponse)
async def create_customer(
    body: CreateCustomerBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    if body.anggota_ref:
        exists = (await db.execute(
            text(
                "SELECT 1 FROM koptumbuh.anggota_koperasi "
                "WHERE anggota_ref=:a AND koperasi_ref=:ref"
            ),
            {"a": body.anggota_ref, "ref": ref},
        )).scalar()
        if not exists:
            raise HTTPException(status_code=400, detail="anggota_ref not found")

    cid = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO koptumbuh.pelanggan_koptumbuh "
            "(pelanggan_id, koperasi_ref, anggota_ref, nama_pelanggan, nomor_whatsapp) "
            "VALUES (:id, :ref, :anggota, :nama, :wa)"
        ),
        {
            "id": cid,
            "ref": ref,
            "anggota": body.anggota_ref,
            "nama": body.nama_pelanggan,
            "wa": body.nomor_whatsapp,
        },
    )
    await db.commit()
    return ApiResponse(data={
        "id": str(cid),
        "nama_pelanggan": body.nama_pelanggan,
        "nomor_whatsapp": body.nomor_whatsapp,
        "anggota_ref": body.anggota_ref,
    })
