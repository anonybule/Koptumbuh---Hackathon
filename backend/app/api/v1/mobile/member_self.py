from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


async def _resolve_anggota_ref(user: dict, db: AsyncSession) -> str | None:
    """Best-effort link: pelanggan by WhatsApp, else anggota by name match."""
    if user.get("anggota_ref"):
        return user["anggota_ref"]
    ref = user["koperasi_ref"]
    wa = user.get("nomor_whatsapp")
    if wa:
        row = (await db.execute(
            text(
                "SELECT anggota_ref FROM koptumbuh.pelanggan_koptumbuh "
                "WHERE koperasi_ref=:ref AND nomor_whatsapp=:wa AND anggota_ref IS NOT NULL "
                "LIMIT 1"
            ),
            {"ref": ref, "wa": wa},
        )).fetchone()
        if row:
            return row[0]
    nama = user.get("nama")
    if nama:
        row = (await db.execute(
            text(
                "SELECT anggota_ref FROM koptumbuh.anggota_koperasi "
                "WHERE koperasi_ref=:ref AND nama ILIKE :nama LIMIT 1"
            ),
            {"ref": ref, "nama": nama},
        )).fetchone()
        if row:
            return row[0]
    return None


@router.get("/my-transactions", response_model=ApiResponse)
async def my_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    anggota = await _resolve_anggota_ref(user, db)
    if not anggota:
        return ApiResponse(data=[], meta=paginate(page, per_page, 0))

    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.relasi_transaksi_pihak r "
            "JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id "
            "WHERE r.anggota_ref=:a AND t.koperasi_ref=:ref"
        ),
        {"a": anggota, "ref": ref},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT t.transaksi_sample_id, t.nama_pelanggan, t.total_pembayaran, "
            "t.status_transaksi, t.metode_pembayaran, t.tanggal_dibuat "
            "FROM koptumbuh.relasi_transaksi_pihak r "
            "JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id "
            "WHERE r.anggota_ref=:a AND t.koperasi_ref=:ref "
            "ORDER BY t.tanggal_dibuat DESC OFFSET :offset LIMIT :limit"
        ),
        {"a": anggota, "ref": ref, "offset": offset, "limit": limit},
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": r[0],
                "customer": r[1],
                "total": float(r[2] or 0),
                "status": r[3],
                "payment_method": r[4],
                "date": str(r[5]) if r[5] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/my-savings", response_model=ApiResponse)
async def my_savings(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    anggota = await _resolve_anggota_ref(user, db)
    if not anggota:
        return ApiResponse(data={"anggota_ref": None, "total": 0, "items": []})

    ref = user["koperasi_ref"]
    total = (await db.execute(
        text(
            "SELECT COALESCE(SUM(jumlah_simpanan), 0) FROM koptumbuh.simpanan_anggota "
            "WHERE anggota_ref=:a AND koperasi_ref=:ref"
        ),
        {"a": anggota, "ref": ref},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT simpanan_ref, periode_pembayaran, jumlah_simpanan, status, "
            "dibuat_pada, dibayar_pada "
            "FROM koptumbuh.simpanan_anggota "
            "WHERE anggota_ref=:a AND koperasi_ref=:ref "
            "ORDER BY dibuat_pada DESC LIMIT 50"
        ),
        {"a": anggota, "ref": ref},
    )).fetchall()

    return ApiResponse(data={
        "anggota_ref": anggota,
        "total": float(total),
        "items": [
            {
                "id": r[0],
                "periode": r[1],
                "jumlah": float(r[2] or 0),
                "status": r[3],
                "created_at": str(r[4]) if r[4] else None,
                "paid_at": str(r[5]) if r[5] else None,
            }
            for r in rows
        ],
    })


@router.get("/my-loans", response_model=ApiResponse)
async def my_loans(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    anggota = await _resolve_anggota_ref(user, db)
    if not anggota:
        return ApiResponse(data=[])

    ref = user["koperasi_ref"]
    # Prefer pinjaman_anggota (migrations); fall back to empty if missing
    try:
        rows = (await db.execute(
            text(
                "SELECT pinjaman_id, jumlah_pinjaman, tenor_bulan, bunga_persen, "
                "angsuran_per_bulan, status, tanggal_mulai, tanggal_jatuh_tempo "
                "FROM koptumbuh.pinjaman_anggota "
                "WHERE anggota_ref=:a AND koperasi_ref=:ref "
                "ORDER BY dibuat_pada DESC"
            ),
            {"a": anggota, "ref": ref},
        )).fetchall()
        return ApiResponse(data=[
            {
                "id": str(r[0]),
                "jumlah": float(r[1] or 0),
                "tenor_bulan": r[2],
                "bunga_persen": float(r[3] or 0),
                "angsuran": float(r[4]) if r[4] is not None else None,
                "status": r[5],
                "mulai": str(r[6]) if r[6] else None,
                "jatuh_tempo": str(r[7]) if r[7] else None,
            }
            for r in rows
        ])
    except Exception:
        await db.rollback()
        return ApiResponse(data=[])
