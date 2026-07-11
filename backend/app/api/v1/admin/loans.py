import uuid
from calendar import monthrange
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-loans"])

VALID_STATUS = {"AKTIF", "LUNAS", "MACET"}


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


class CreateLoanBody(BaseModel):
    anggota_ref: str
    jumlah_pinjaman: float = Field(gt=0)
    tenor_bulan: int = Field(gt=0)
    bunga_persen: float = Field(default=0, ge=0)


class PatchLoanBody(BaseModel):
    status: str


def _loan_dict(r) -> dict:
    return {
        "id": str(r[0]),
        "koperasi_ref": r[1],
        "anggota_ref": r[2],
        "jumlah_pinjaman": float(r[3] or 0),
        "tenor_bulan": r[4],
        "bunga_persen": float(r[5] or 0),
        "angsuran_per_bulan": float(r[6]) if r[6] is not None else None,
        "total_pengembalian": float(r[7]) if r[7] is not None else None,
        "status": r[8],
        "tanggal_mulai": str(r[9]) if r[9] else None,
        "tanggal_jatuh_tempo": str(r[10]) if r[10] else None,
        "dibuat_pada": str(r[11]) if len(r) > 11 and r[11] else None,
    }


LOAN_COLS = (
    "pinjaman_id, koperasi_ref, anggota_ref, jumlah_pinjaman, tenor_bulan, "
    "bunga_persen, angsuran_per_bulan, total_pengembalian, status, "
    "tanggal_mulai, tanggal_jatuh_tempo, dibuat_pada"
)


@router.get("/loans", response_model=ApiResponse)
async def list_loans(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str | None = None,
    anggota_ref: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    where = ["koperasi_ref=:r"]
    params: dict = {"r": user["koperasi_ref"], "off": offset, "lim": limit}
    if status:
        where.append("status=:st")
        params["st"] = status
    if anggota_ref:
        where.append("anggota_ref=:a")
        params["a"] = anggota_ref
    clause = " AND ".join(where)
    try:
        total = (
            await db.execute(
                text(f"SELECT COUNT(*) FROM koptumbuh.pinjaman_anggota WHERE {clause}"),
                params,
            )
        ).scalar() or 0
        result = await db.execute(
            text(
                f"SELECT {LOAN_COLS} FROM koptumbuh.pinjaman_anggota WHERE {clause} "
                f"ORDER BY dibuat_pada DESC NULLS LAST OFFSET :off LIMIT :lim"
            ),
            params,
        )
        return ApiResponse(
            data=[_loan_dict(r) for r in result.fetchall()],
            meta=paginate(page, per_page, total),
        )
    except Exception:
        await db.rollback()
        return ApiResponse(data=[], meta=paginate(page, per_page, 0))


@router.get("/loans/{loan_id}", response_model=ApiResponse)
async def get_loan(
    loan_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(
            text(
                f"SELECT {LOAN_COLS} FROM koptumbuh.pinjaman_anggota "
                "WHERE pinjaman_id=:id AND koperasi_ref=:r"
            ),
            {"id": loan_id, "r": user["koperasi_ref"]},
        )
        row = result.fetchone()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Loan not found")
    if not row:
        raise HTTPException(status_code=404, detail="Loan not found")
    return ApiResponse(data=_loan_dict(row))


@router.post("/loans", response_model=ApiResponse)
async def create_loan(
    body: CreateLoanBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    member = (
        await db.execute(
            text(
                "SELECT 1 FROM koptumbuh.anggota_koperasi "
                "WHERE anggota_ref=:a AND koperasi_ref=:r"
            ),
            {"a": body.anggota_ref, "r": ref},
        )
    ).scalar()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this cooperative")

    bunga = body.bunga_persen or 0
    total = body.jumlah_pinjaman * (1 + bunga / 100.0)
    angsuran = round(total / body.tenor_bulan, 2) if body.tenor_bulan else total
    mulai = date.today()
    jatuh_tempo = _add_months(mulai, body.tenor_bulan)
    loan_id = str(uuid.uuid4())

    try:
        await db.execute(
            text(
                "INSERT INTO koptumbuh.pinjaman_anggota "
                "(pinjaman_id, koperasi_ref, anggota_ref, jumlah_pinjaman, tenor_bulan, "
                " bunga_persen, angsuran_per_bulan, total_pengembalian, status, "
                " tanggal_mulai, tanggal_jatuh_tempo) "
                "VALUES (:id, :r, :a, :jumlah, :tenor, :bunga, :angsuran, :total, "
                " 'AKTIF', :mulai, :jatuh)"
            ),
            {
                "id": loan_id,
                "r": ref,
                "a": body.anggota_ref,
                "jumlah": body.jumlah_pinjaman,
                "tenor": body.tenor_bulan,
                "bunga": bunga,
                "angsuran": angsuran,
                "total": round(total, 2),
                "mulai": mulai,
                "jatuh": jatuh_tempo,
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=503, detail=f"Loans table unavailable: {e}")

    return ApiResponse(
        data={
            "id": loan_id,
            "anggota_ref": body.anggota_ref,
            "jumlah_pinjaman": body.jumlah_pinjaman,
            "tenor_bulan": body.tenor_bulan,
            "bunga_persen": bunga,
            "angsuran_per_bulan": angsuran,
            "total_pengembalian": round(total, 2),
            "status": "AKTIF",
            "tanggal_mulai": str(mulai),
            "tanggal_jatuh_tempo": str(jatuh_tempo),
        }
    )


@router.patch("/loans/{loan_id}", response_model=ApiResponse)
async def patch_loan(
    loan_id: str,
    body: PatchLoanBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    status = (body.status or "").upper()
    if status not in VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(VALID_STATUS)}")

    try:
        result = await db.execute(
            text(
                "UPDATE koptumbuh.pinjaman_anggota "
                "SET status=:st, diperbarui_pada=NOW() "
                "WHERE pinjaman_id=:id AND koperasi_ref=:r "
                "RETURNING pinjaman_id, status"
            ),
            {"st": status, "id": loan_id, "r": user["koperasi_ref"]},
        )
        row = result.fetchone()
        if not row:
            await db.rollback()
            raise HTTPException(status_code=404, detail="Loan not found")
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=503, detail=f"Loans table unavailable: {e}")

    return ApiResponse(data={"id": str(row[0]), "status": row[1]})
