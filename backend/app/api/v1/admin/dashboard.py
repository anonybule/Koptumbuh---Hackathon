from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


async def _fetch_or_fallback(db: AsyncSession, primary: str, fallback: str, params: dict):
    """Try a view query; on failure roll back and run fallback SQL."""
    try:
        result = await db.execute(text(primary), params)
        return result.fetchall()
    except Exception:
        await db.rollback()
        result = await db.execute(text(fallback), params)
        return result.fetchall()


@router.get("/dashboard/kpi", response_model=ApiResponse)
async def kpi(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    sales = await db.execute(
        text(
            "SELECT COALESCE(SUM(total_pembayaran),0) FROM koptumbuh.transaksi_penjualan "
            "WHERE koperasi_ref=:r AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')"
        ),
        {"r": ref},
    )
    tx = await db.execute(
        text("SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r"),
        {"r": ref},
    )
    stock = await db.execute(
        text("SELECT COUNT(*) FROM koptumbuh.inventaris_produk WHERE koperasi_ref=:r AND stok < 5"),
        {"r": ref},
    )
    members = await db.execute(
        text("SELECT COUNT(*) FROM koptumbuh.anggota_koperasi WHERE koperasi_ref=:r"),
        {"r": ref},
    )
    return ApiResponse(
        data={
            "total_revenue": float(sales.scalar() or 0),
            "total_transactions": tx.scalar() or 0,
            "low_stock": stock.scalar() or 0,
            "total_members": members.scalar() or 0,
        }
    )


@router.get("/dashboard/sales", response_model=ApiResponse)
async def sales(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT hari::date, omzet, jumlah_transaksi FROM koptumbuh.v_penjualan_harian "
        "WHERE koperasi_ref=:r ORDER BY hari DESC LIMIT 30",
        "SELECT DATE_TRUNC('day', COALESCE(tanggal_dibuat, dibuat_pada))::date AS hari, "
        "SUM(COALESCE(total_pembayaran,0)) AS omzet, COUNT(*) AS jumlah_transaksi "
        "FROM koptumbuh.transaksi_penjualan "
        "WHERE koperasi_ref=:r AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "GROUP BY 1 ORDER BY 1 DESC LIMIT 30",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(data=[{"date": str(r[0]), "revenue": float(r[1] or 0), "count": r[2]} for r in rows])


@router.get("/dashboard/top-products", response_model=ApiResponse)
async def top_products(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT nama_produk, jumlah_terjual, nilai_penjualan FROM koptumbuh.v_produk_terlaris "
        "WHERE koperasi_ref=:r ORDER BY jumlah_terjual DESC LIMIT 10",
        "SELECT COALESCE(MAX(p.nama_produk), MAX(b.nama_produk)) AS nama_produk, "
        "SUM(COALESCE(b.jumlah_keluar,0)) AS jumlah_terjual, "
        "SUM(COALESCE(b.total_nilai,0)) AS nilai_penjualan "
        "FROM koptumbuh.barang_keluar_produk b "
        "LEFT JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id=b.produk_sample_id "
        "WHERE b.koperasi_ref=:r AND COALESCE(b.status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "GROUP BY b.produk_sample_id ORDER BY jumlah_terjual DESC LIMIT 10",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(data=[{"name": r[0], "qty": float(r[1] or 0), "revenue": float(r[2] or 0)} for r in rows])


@router.get("/dashboard/active-members", response_model=ApiResponse)
async def active_members(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT nama, jumlah_transaksi, total_belanja, status_aktivitas FROM koptumbuh.v_anggota_aktif "
        "WHERE koperasi_ref=:r ORDER BY total_belanja DESC LIMIT 20",
        "SELECT a.nama, COUNT(DISTINCT r.transaksi_sample_id) AS jumlah_transaksi, "
        "COALESCE(SUM(t.total_pembayaran),0) AS total_belanja, "
        "CASE WHEN MAX(t.tanggal_dibuat) IS NULL THEN 'TIDAK_AKTIF' "
        "WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '30 days' THEN 'TIDAK_AKTIF_30_HARI' "
        "WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '7 days' THEN 'KURANG_AKTIF' ELSE 'AKTIF' END "
        "FROM koptumbuh.anggota_koperasi a "
        "LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref "
        "LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
        "AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "WHERE a.koperasi_ref=:r "
        "GROUP BY a.anggota_ref, a.nama ORDER BY total_belanja DESC LIMIT 20",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[{"name": r[0], "tx_count": r[1], "total": float(r[2] or 0), "status": r[3]} for r in rows]
    )


@router.get("/dashboard/margin", response_model=ApiResponse)
async def margins(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT nama_produk, harga_beli, harga_jual, margin_nominal, margin_persen, total_profit "
        "FROM koptumbuh.v_margin_produk WHERE koperasi_ref=:r ORDER BY total_profit DESC",
        "SELECT p.nama_produk, latest_bm.harga_beli, latest_bm.harga_jual, "
        "(latest_bm.harga_jual - latest_bm.harga_beli) AS margin_nominal, "
        "CASE WHEN latest_bm.harga_beli > 0 THEN ROUND(((latest_bm.harga_jual - latest_bm.harga_beli) "
        "/ latest_bm.harga_beli * 100)::numeric, 1) ELSE 0 END AS margin_persen, "
        "(latest_bm.harga_jual - latest_bm.harga_beli) * COALESCE(sales.total_terjual,0) AS total_profit "
        "FROM koptumbuh.produk_koperasi p "
        "LEFT JOIN LATERAL (SELECT harga_beli, harga_jual FROM koptumbuh.barang_masuk_produk "
        "WHERE produk_sample_id=p.produk_sample_id AND koperasi_ref=p.koperasi_ref "
        "AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') "
        "ORDER BY tanggal_masuk DESC LIMIT 1) latest_bm ON TRUE "
        "LEFT JOIN (SELECT produk_sample_id, koperasi_ref, SUM(jumlah_keluar) AS total_terjual "
        "FROM koptumbuh.barang_keluar_produk "
        "WHERE COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "GROUP BY produk_sample_id, koperasi_ref) sales "
        "ON sales.produk_sample_id=p.produk_sample_id AND sales.koperasi_ref=p.koperasi_ref "
        "WHERE p.koperasi_ref=:r ORDER BY total_profit DESC NULLS LAST",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[
            {
                "name": r[0],
                "buy": float(r[1] or 0),
                "sell": float(r[2] or 0),
                "margin": float(r[3] or 0),
                "margin_pct": float(r[4] or 0),
                "profit": float(r[5] or 0),
            }
            for r in rows
        ]
    )


@router.get("/dashboard/stock-reconciliation", response_model=ApiResponse)
async def stock_reconciliation(
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    rows = await _fetch_or_fallback(
        db,
        "SELECT produk_sample_id, nama_produk, stok_terhitung, stok_snapshot, selisih, status_rekonsiliasi "
        "FROM koptumbuh.v_rekonsiliasi_stok WHERE koperasi_ref=:r "
        "ORDER BY CASE status_rekonsiliasi WHEN 'MISMATCH' THEN 0 WHEN 'SNAPSHOT_MISSING' THEN 1 ELSE 2 END, "
        "ABS(COALESCE(selisih,0)) DESC",
        "WITH masuk AS ("
        "  SELECT produk_sample_id, SUM(COALESCE(jumlah_masuk,0)) AS total_masuk "
        "  FROM koptumbuh.barang_masuk_produk WHERE koperasi_ref=:r "
        "  AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') GROUP BY produk_sample_id"
        "), keluar AS ("
        "  SELECT produk_sample_id, SUM(COALESCE(jumlah_keluar,0)) AS total_keluar "
        "  FROM koptumbuh.barang_keluar_produk WHERE koperasi_ref=:r "
        "  AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') GROUP BY produk_sample_id"
        "), adj AS ("
        "  SELECT produk_sample_id, SUM(quantity_delta) AS total_adj "
        "  FROM koptumbuh.penyesuaian_stok WHERE koperasi_ref=:r GROUP BY produk_sample_id"
        ") "
        "SELECT p.produk_sample_id, p.nama_produk, "
        "COALESCE(m.total_masuk,0)-COALESCE(k.total_keluar,0)+COALESCE(a.total_adj,0) AS stok_terhitung, "
        "i.stok AS stok_snapshot, "
        "COALESCE(i.stok,0)-(COALESCE(m.total_masuk,0)-COALESCE(k.total_keluar,0)+COALESCE(a.total_adj,0)) AS selisih, "
        "CASE WHEN i.inventaris_ref IS NULL THEN 'SNAPSHOT_MISSING' "
        "WHEN COALESCE(i.stok,0)=COALESCE(m.total_masuk,0)-COALESCE(k.total_keluar,0)+COALESCE(a.total_adj,0) "
        "THEN 'MATCH' ELSE 'MISMATCH' END AS status_rekonsiliasi "
        "FROM koptumbuh.produk_koperasi p "
        "LEFT JOIN masuk m ON m.produk_sample_id=p.produk_sample_id "
        "LEFT JOIN keluar k ON k.produk_sample_id=p.produk_sample_id "
        "LEFT JOIN adj a ON a.produk_sample_id=p.produk_sample_id "
        "LEFT JOIN koptumbuh.inventaris_produk i ON i.produk_sample_id=p.produk_sample_id AND i.koperasi_ref=p.koperasi_ref "
        "WHERE p.koperasi_ref=:r",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[
            {
                "produk_sample_id": r[0],
                "nama_produk": r[1],
                "stok_terhitung": float(r[2] or 0),
                "stok_snapshot": float(r[3] or 0) if r[3] is not None else None,
                "selisih": float(r[4] or 0),
                "status": r[5],
            }
            for r in rows
        ]
    )


@router.get("/dashboard/slow-moving", response_model=ApiResponse)
async def slow_moving(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT produk_sample_id, nama_produk, stok_saat_ini, terakhir_terjual, hari_tanpa_penjualan "
        "FROM koptumbuh.v_produk_lambat_bergerak WHERE koperasi_ref=:r "
        "ORDER BY hari_tanpa_penjualan DESC",
        "SELECT p.produk_sample_id, p.nama_produk, i.stok, latest_sale.terakhir_terjual, "
        "CASE WHEN latest_sale.terakhir_terjual IS NOT NULL "
        "THEN (CURRENT_DATE - latest_sale.terakhir_terjual::date) ELSE 999 END "
        "FROM koptumbuh.produk_koperasi p "
        "JOIN koptumbuh.inventaris_produk i ON i.produk_sample_id=p.produk_sample_id "
        "AND i.koperasi_ref=p.koperasi_ref "
        "LEFT JOIN LATERAL ("
        "  SELECT MAX(tanggal_keluar) AS terakhir_terjual FROM koptumbuh.barang_keluar_produk "
        "  WHERE produk_sample_id=p.produk_sample_id AND koperasi_ref=p.koperasi_ref "
        "  AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')"
        ") latest_sale ON TRUE "
        "WHERE p.koperasi_ref=:r AND i.stok > 0 "
        "AND (latest_sale.terakhir_terjual IS NULL OR latest_sale.terakhir_terjual < CURRENT_DATE - INTERVAL '14 days') "
        "ORDER BY 5 DESC",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[
            {
                "produk_sample_id": r[0],
                "nama_produk": r[1],
                "stok": float(r[2] or 0),
                "terakhir_terjual": str(r[3]) if r[3] else None,
                "hari_tanpa_penjualan": int(r[4] or 0),
            }
            for r in rows
        ]
    )


@router.get("/dashboard/segmentation", response_model=ApiResponse)
async def segmentation(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT anggota_ref, nama, frekuensi, moneter, resensi_hari, segmentasi, status_retensi "
        "FROM koptumbuh.v_segmentasi_anggota WHERE koperasi_ref=:r "
        "ORDER BY moneter DESC",
        "WITH rfm AS ("
        "  SELECT a.anggota_ref, a.nama, "
        "  COUNT(DISTINCT r.transaksi_sample_id) AS frekuensi, "
        "  COALESCE(SUM(t.total_pembayaran),0) AS moneter, "
        "  CASE WHEN MAX(t.tanggal_dibuat) IS NOT NULL "
        "  THEN (CURRENT_DATE - MAX(t.tanggal_dibuat)::date) ELSE 999 END AS resensi_hari "
        "  FROM koptumbuh.anggota_koperasi a "
        "  LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref "
        "  LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
        "  AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "  WHERE a.koperasi_ref=:r "
        "  GROUP BY a.anggota_ref, a.nama"
        ") "
        "SELECT anggota_ref, nama, frekuensi, moneter, resensi_hari, "
        "CASE WHEN frekuensi >= 10 AND moneter >= 500000 THEN 'DIAMOND' "
        "WHEN frekuensi >= 5 AND moneter >= 250000 THEN 'EMAS' "
        "WHEN frekuensi >= 2 AND moneter >= 100000 THEN 'PERAK' "
        "WHEN frekuensi >= 1 THEN 'PERUNGGU' ELSE 'TIDAK_AKTIF' END, "
        "CASE WHEN resensi_hari <= 7 AND frekuensi >= 5 THEN 'PELANGGAN_SETIA' "
        "WHEN resensi_hari <= 30 AND frekuensi >= 3 THEN 'PELANGGAN_REGULER' "
        "WHEN resensi_hari <= 60 THEN 'PELANGGAN_JARANG' "
        "WHEN resensi_hari <= 180 THEN 'RISIKO_HILANG' ELSE 'HILANG' END "
        "FROM rfm ORDER BY moneter DESC",
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[
            {
                "anggota_ref": r[0],
                "nama": r[1],
                "frekuensi": int(r[2] or 0),
                "moneter": float(r[3] or 0),
                "resensi_hari": int(r[4] or 0),
                "segmentasi": r[5],
                "status_retensi": r[6],
            }
            for r in rows
        ]
    )


@router.get("/dashboard/retention", response_model=ApiResponse)
async def retention(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _fetch_or_fallback(
        db,
        "SELECT anggota_ref, nama, frekuensi, moneter, resensi_hari, segmentasi, status_retensi "
        "FROM koptumbuh.v_segmentasi_anggota WHERE koperasi_ref=:r "
        "ORDER BY resensi_hari DESC",
        "WITH rfm AS ("
        "  SELECT a.anggota_ref, a.nama, "
        "  COUNT(DISTINCT r.transaksi_sample_id) AS frekuensi, "
        "  COALESCE(SUM(t.total_pembayaran),0) AS moneter, "
        "  CASE WHEN MAX(t.tanggal_dibuat) IS NOT NULL "
        "  THEN (CURRENT_DATE - MAX(t.tanggal_dibuat)::date) ELSE 999 END AS resensi_hari "
        "  FROM koptumbuh.anggota_koperasi a "
        "  LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref "
        "  LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
        "  AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled') "
        "  WHERE a.koperasi_ref=:r "
        "  GROUP BY a.anggota_ref, a.nama"
        ") "
        "SELECT anggota_ref, nama, frekuensi, moneter, resensi_hari, "
        "CASE WHEN frekuensi >= 10 AND moneter >= 500000 THEN 'DIAMOND' "
        "WHEN frekuensi >= 5 AND moneter >= 250000 THEN 'EMAS' "
        "WHEN frekuensi >= 2 AND moneter >= 100000 THEN 'PERAK' "
        "WHEN frekuensi >= 1 THEN 'PERUNGGU' ELSE 'TIDAK_AKTIF' END, "
        "CASE WHEN resensi_hari <= 7 AND frekuensi >= 5 THEN 'PELANGGAN_SETIA' "
        "WHEN resensi_hari <= 30 AND frekuensi >= 3 THEN 'PELANGGAN_REGULER' "
        "WHEN resensi_hari <= 60 THEN 'PELANGGAN_JARANG' "
        "WHEN resensi_hari <= 180 THEN 'RISIKO_HILANG' ELSE 'HILANG' END "
        "FROM rfm ORDER BY resensi_hari DESC",
        {"r": user["koperasi_ref"]},
    )
    members = [
        {
            "anggota_ref": r[0],
            "nama": r[1],
            "frekuensi": int(r[2] or 0),
            "moneter": float(r[3] or 0),
            "resensi_hari": int(r[4] or 0),
            "segmentasi": r[5],
            "status_retensi": r[6],
        }
        for r in rows
    ]
    counts: dict[str, int] = {}
    for m in members:
        key = m["status_retensi"] or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return ApiResponse(data={"counts": counts, "members": members})


async def _shu_rows(db: AsyncSession, koperasi_ref: str):
    from app.services.shu_service import compute_shu_monthly

    rows = await compute_shu_monthly(db, koperasi_ref)
    # Adapt to legacy tuple shape for _format_shu
    return [(r["bulan"], r["total_omzet"], r["jumlah_transaksi"], r["estimasi_shu"]) for r in rows]


def _format_shu(rows) -> list[dict]:
    return [
        {
            "bulan": str(r[0]) if r[0] else None,
            "total_omzet": float(r[1] or 0),
            "jumlah_transaksi": int(r[2] or 0),
            "estimasi_shu": float(r[3] or 0),
        }
        for r in rows
    ]


@router.get("/dashboard/shu", response_model=ApiResponse)
async def dashboard_shu(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _shu_rows(db, user["koperasi_ref"])
    return ApiResponse(data=_format_shu(rows))


@router.get("/shu/estimate", response_model=ApiResponse)
async def shu_estimate(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _shu_rows(db, user["koperasi_ref"])
    return ApiResponse(data=_format_shu(rows))


async def _price_comparison_rows(db: AsyncSession, koperasi_ref: str):
    return await _fetch_or_fallback(
        db,
        "SELECT v.produk_sample_id, v.nama_produk, v.harga_kita, v.harga_pasar_rata, "
        "v.jumlah_sumber, v.status_harga "
        "FROM koptumbuh.v_perbandingan_harga v "
        "JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id=v.produk_sample_id "
        "WHERE p.koperasi_ref=:r ORDER BY v.nama_produk",
        "WITH our AS ("
        "  SELECT DISTINCT ON (produk_sample_id) produk_sample_id, harga_jual "
        "  FROM koptumbuh.barang_masuk_produk "
        "  WHERE koperasi_ref=:r AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') "
        "  ORDER BY produk_sample_id, tanggal_masuk DESC"
        "), market AS ("
        "  SELECT produk_sample_id, COUNT(*) AS jumlah, ROUND(AVG(harga),0) AS rata "
        "  FROM koptumbuh.harga_pasar WHERE kadaluarsa_pada > NOW() GROUP BY produk_sample_id"
        ") "
        "SELECT p.produk_sample_id, p.nama_produk, o.harga_jual, m.rata, m.jumlah, "
        "CASE WHEN m.rata IS NULL THEN 'NO_DATA' WHEN o.harga_jual <= m.rata THEN 'TERMURAH' "
        "ELSE 'LEBIH_MAHAL' END "
        "FROM koptumbuh.produk_koperasi p "
        "JOIN our o ON o.produk_sample_id=p.produk_sample_id "
        "LEFT JOIN market m ON m.produk_sample_id=p.produk_sample_id "
        "WHERE p.koperasi_ref=:r ORDER BY p.nama_produk",
        {"r": koperasi_ref},
    )


def _format_price_comparison(rows) -> list[dict]:
    return [
        {
            "produk_sample_id": r[0],
            "nama_produk": r[1],
            "harga_kita": float(r[2] or 0) if r[2] is not None else None,
            "harga_pasar_rata": float(r[3] or 0) if r[3] is not None else None,
            "jumlah_sumber": int(r[4] or 0) if r[4] is not None else 0,
            "status_harga": r[5],
        }
        for r in rows
    ]


@router.get("/dashboard/price-comparison", response_model=ApiResponse)
async def dashboard_price_comparison(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = await _price_comparison_rows(db, user["koperasi_ref"])
    return ApiResponse(data=_format_price_comparison(rows))


@router.get("/price-comparison", response_model=ApiResponse)
async def price_comparison(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await _price_comparison_rows(db, user["koperasi_ref"])
    return ApiResponse(data=_format_price_comparison(rows))


@router.get("/price-comparison/history", response_model=ApiResponse)
async def price_comparison_history(
    produk_sample_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    where = [
        "(h.produk_sample_id IS NULL OR h.produk_sample_id IN ("
        "SELECT produk_sample_id FROM koptumbuh.produk_koperasi WHERE koperasi_ref=:r))"
    ]
    params: dict = {"r": ref}
    if produk_sample_id:
        where.append("h.produk_sample_id=:pid")
        params["pid"] = produk_sample_id
    clause = " AND ".join(where)
    try:
        result = await db.execute(
            text(
                f"SELECT h.harga_pasar_id, h.produk_sample_id, h.nama_produk_mentah, h.harga, "
                f"h.nama_toko, h.jenis_toko, h.kab_kota, h.sumber_data, h.tanggal_lapor, h.kadaluarsa_pada "
                f"FROM koptumbuh.harga_pasar h WHERE {clause} "
                f"ORDER BY h.tanggal_lapor DESC LIMIT 200"
            ),
            params,
        )
        rows = result.fetchall()
    except Exception:
        await db.rollback()
        return ApiResponse(data=[])
    return ApiResponse(
        data=[
            {
                "harga_pasar_id": str(r[0]),
                "produk_sample_id": r[1],
                "nama_produk": r[2],
                "harga": float(r[3] or 0),
                "nama_toko": r[4],
                "jenis_toko": r[5],
                "kab_kota": r[6],
                "sumber_data": r[7],
                "tanggal_lapor": str(r[8]) if r[8] else None,
                "kadaluarsa_pada": str(r[9]) if r[9] else None,
            }
            for r in rows
        ]
    )


@router.get("/dashboard/member-activity", response_model=ApiResponse)
async def member_activity(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Prefer v_aktivitas_anggota; fall back to v_anggota_aktif; then raw SQL
    try:
        result = await db.execute(
            text(
                "SELECT nama, jumlah_transaksi, total_belanja, transaksi_terakhir "
                "FROM koptumbuh.v_aktivitas_anggota WHERE koperasi_ref=:r "
                "ORDER BY total_belanja DESC LIMIT 50"
            ),
            {"r": user["koperasi_ref"]},
        )
        rows = result.fetchall()
        return ApiResponse(
            data=[
                {
                    "name": r[0],
                    "tx_count": r[1],
                    "total": float(r[2] or 0),
                    "last_tx": str(r[3]) if r[3] else None,
                }
                for r in rows
            ]
        )
    except Exception:
        await db.rollback()

    try:
        result = await db.execute(
            text(
                "SELECT nama, jumlah_transaksi, total_belanja, transaksi_terakhir, status_aktivitas "
                "FROM koptumbuh.v_anggota_aktif WHERE koperasi_ref=:r "
                "ORDER BY total_belanja DESC LIMIT 50"
            ),
            {"r": user["koperasi_ref"]},
        )
        rows = result.fetchall()
        return ApiResponse(
            data=[
                {
                    "name": r[0],
                    "tx_count": r[1],
                    "total": float(r[2] or 0),
                    "last_tx": str(r[3]) if r[3] else None,
                    "status": r[4],
                }
                for r in rows
            ]
        )
    except Exception:
        await db.rollback()

    result = await db.execute(
        text(
            "SELECT a.nama, COUNT(DISTINCT r.transaksi_sample_id), "
            "COALESCE(SUM(t.total_pembayaran),0), MAX(t.tanggal_dibuat) "
            "FROM koptumbuh.anggota_koperasi a "
            "LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref "
            "LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
            "WHERE a.koperasi_ref=:r "
            "GROUP BY a.anggota_ref, a.nama ORDER BY 3 DESC LIMIT 50"
        ),
        {"r": user["koperasi_ref"]},
    )
    return ApiResponse(
        data=[
            {
                "name": r[0],
                "tx_count": r[1],
                "total": float(r[2] or 0),
                "last_tx": str(r[3]) if r[3] else None,
            }
            for r in result.fetchall()
        ]
    )
