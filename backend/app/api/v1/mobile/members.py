from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit, mask_nik

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/members/search", response_model=ApiResponse)
async def search_members(
    q: str = Query(..., min_length=1),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    rows = (await db.execute(
        text(
            "SELECT anggota_ref, nama, nik, jenis_kelamin, status_keanggotaan, tanggal_terdaftar "
            "FROM koptumbuh.anggota_koperasi "
            "WHERE koperasi_ref=:ref AND (nama ILIKE :q OR nik ILIKE :q) "
            "ORDER BY nama LIMIT 30"
        ),
        {"ref": ref, "q": f"%{q}%"},
    )).fetchall()

    return ApiResponse(data=[
        {
            "id": r[0],
            "nama": r[1],
            "nik": mask_nik(r[2]),
            "gender": r[3],
            "status": r[4],
            "registered": str(r[5]) if r[5] else None,
        }
        for r in rows
    ])


@router.get("/members/{anggota_id}", response_model=ApiResponse)
async def member_detail(
    anggota_id: str,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    m = (await db.execute(
        text(
            "SELECT anggota_ref, nama, nik, jenis_kelamin, status_keanggotaan, "
            "tanggal_terdaftar, pekerjaan "
            "FROM koptumbuh.anggota_koperasi "
            "WHERE anggota_ref=:id AND koperasi_ref=:ref"
        ),
        {"id": anggota_id, "ref": ref},
    )).fetchone()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")

    savings_sum = (await db.execute(
        text(
            "SELECT COALESCE(SUM(jumlah_simpanan), 0) FROM koptumbuh.simpanan_anggota "
            "WHERE anggota_ref=:id AND koperasi_ref=:ref"
        ),
        {"id": anggota_id, "ref": ref},
    )).scalar() or 0

    txs = (await db.execute(
        text(
            "SELECT t.transaksi_sample_id, t.nama_pelanggan, t.total_pembayaran, "
            "t.status_transaksi, t.tanggal_dibuat "
            "FROM koptumbuh.relasi_transaksi_pihak r "
            "JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id "
            "WHERE r.anggota_ref=:id AND t.koperasi_ref=:ref "
            "ORDER BY t.tanggal_dibuat DESC LIMIT 10"
        ),
        {"id": anggota_id, "ref": ref},
    )).fetchall()

    return ApiResponse(data={
        "id": m[0],
        "nama": m[1],
        "nik": mask_nik(m[2]),
        "gender": m[3],
        "status": m[4],
        "registered": str(m[5]) if m[5] else None,
        "pekerjaan": m[6],
        "savings_total": float(savings_sum),
        "recent_transactions": [
            {
                "id": r[0],
                "customer": r[1],
                "total": float(r[2] or 0),
                "status": r[3],
                "date": str(r[4]) if r[4] else None,
            }
            for r in txs
        ],
    })
