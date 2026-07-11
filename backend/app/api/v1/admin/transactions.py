from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-transactions"])


@router.get("/transactions", response_model=ApiResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["t.koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if status:
        where.append("t.status_transaksi=:st")
        params["st"] = status
    if date_from:
        where.append("COALESCE(t.tanggal_dibuat, t.dibuat_pada)::date >= :df")
        params["df"] = date_from
    if date_to:
        where.append("COALESCE(t.tanggal_dibuat, t.dibuat_pada)::date <= :dt")
        params["dt"] = date_to
    if q:
        where.append("(t.nama_pelanggan ILIKE :q OR t.transaksi_sample_id ILIKE :q)")
        params["q"] = f"%{q}%"
    clause = " AND ".join(where)

    total = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan t WHERE {clause}"),
            params,
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT t.transaksi_sample_id, t.nama_pelanggan, t.total_pembayaran, t.status_transaksi, "
            f"t.metode_pembayaran, t.tanggal_dibuat, s.sumber, s.pesan_id "
            f"FROM koptumbuh.transaksi_penjualan t "
            f"LEFT JOIN koptumbuh.transaksi_sumber s ON s.transaksi_sample_id = t.transaksi_sample_id "
            f"WHERE {clause} "
            f"ORDER BY t.tanggal_dibuat DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "customer": r[1],
                "total": float(r[2] or 0),
                "status": r[3],
                "method": r[4],
                "date": str(r[5]) if r[5] else None,
                "sumber": r[6],
                "pesan_id": str(r[7]) if r[7] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )
