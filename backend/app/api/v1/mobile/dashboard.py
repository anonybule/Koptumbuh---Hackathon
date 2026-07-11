from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/dashboard/summary", response_model=ApiResponse)
async def dashboard_summary(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mobile dashboard: today's sales, alerts, pending recs, recent transactions."""
    ref = user["koperasi_ref"]
    today_sales = await db.execute(
        text(
            "SELECT COALESCE(SUM(total_pembayaran), 0) FROM koptumbuh.transaksi_penjualan "
            "WHERE koperasi_ref = :ref AND DATE(tanggal_dibuat) = CURRENT_DATE "
            "AND COALESCE(status_transaksi, '') NOT IN ('Refund', 'Cancelled')"
        ),
        {"ref": ref},
    )
    tx_count = await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan "
            "WHERE koperasi_ref = :ref AND DATE(tanggal_dibuat) = CURRENT_DATE"
        ),
        {"ref": ref},
    )
    stock_alerts = await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.inventaris_produk "
            "WHERE koperasi_ref=:ref AND stok < 5"
        ),
        {"ref": ref},
    )
    pending_recs = await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.rekomendasi "
            "WHERE koperasi_ref=:ref AND status='NEW'"
        ),
        {"ref": ref},
    )
    unread_msgs = await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.pesan_masuk "
            "WHERE koperasi_ref=:ref AND status IN ('PARSED','NEEDS_REVIEW')"
        ),
        {"ref": ref},
    )
    recent = await db.execute(
        text(
            "SELECT transaksi_sample_id, nama_pelanggan, total_pembayaran, "
            "status_transaksi, metode_pembayaran, tanggal_dibuat "
            "FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:ref "
            "ORDER BY tanggal_dibuat DESC LIMIT 5"
        ),
        {"ref": ref},
    )
    low_stock = await db.execute(
        text(
            "SELECT produk_sample_id, nama_produk, stok FROM koptumbuh.inventaris_produk "
            "WHERE koperasi_ref=:ref AND stok < 5 ORDER BY stok ASC LIMIT 5"
        ),
        {"ref": ref},
    )

    return ApiResponse(data={
        "today_sales": float(today_sales.scalar() or 0),
        "transaction_count": tx_count.scalar() or 0,
        "stock_alerts": stock_alerts.scalar() or 0,
        "pending_recommendations": pending_recs.scalar() or 0,
        "pending_messages": unread_msgs.scalar() or 0,
        "low_stock_items": [
            {"id": r[0], "nama_produk": r[1], "stok": float(r[2] or 0)}
            for r in low_stock.fetchall()
        ],
        "recent_transactions": [
            {
                "id": r[0],
                "customer": r[1],
                "total": float(r[2] or 0),
                "status": r[3],
                "payment_method": r[4],
                "date": str(r[5]) if r[5] else None,
            }
            for r in recent.fetchall()
        ],
    })
