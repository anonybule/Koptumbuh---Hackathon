from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/products", response_model=ApiResponse)
async def list_products(
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "p.koperasi_ref = :ref"
    params: dict = {"ref": ref, "offset": offset, "limit": limit}
    if q:
        where += " AND p.nama_produk ILIKE :q"
        params["q"] = f"%{q}%"

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM koptumbuh.produk_koperasi p WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("offset", "limit")},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            f"""SELECT p.produk_sample_id, p.nama_produk, p.unit, p.kode_barcode,
                       COALESCE(i.stok, 0) AS stok,
                       bm.harga_jual, bm.harga_beli
                FROM koptumbuh.produk_koperasi p
                LEFT JOIN koptumbuh.inventaris_produk i
                  ON i.produk_sample_id = p.produk_sample_id AND i.koperasi_ref = p.koperasi_ref
                LEFT JOIN LATERAL (
                  SELECT harga_jual, harga_beli FROM koptumbuh.barang_masuk_produk
                  WHERE produk_sample_id = p.produk_sample_id AND koperasi_ref = p.koperasi_ref
                    AND COALESCE(status,'') NOT IN ('Rejected','Cancelled')
                  ORDER BY tanggal_masuk DESC LIMIT 1
                ) bm ON TRUE
                WHERE {where}
                ORDER BY p.nama_produk
                OFFSET :offset LIMIT :limit"""
        ),
        params,
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": r[0],
                "nama_produk": r[1],
                "unit": r[2],
                "barcode": r[3],
                "stok": float(r[4] or 0),
                "harga_jual": float(r[5]) if r[5] is not None else None,
                "harga_beli": float(r[6]) if r[6] is not None else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/products/{produk_id}/stock", response_model=ApiResponse)
async def product_stock(
    produk_id: str,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    inv = (await db.execute(
        text(
            "SELECT inventaris_ref, nama_produk, stok, kode_barcode, lokasi_simpan "
            "FROM koptumbuh.inventaris_produk "
            "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
        ),
        {"pid": produk_id, "ref": ref},
    )).fetchone()
    if not inv:
        raise HTTPException(status_code=404, detail="Product inventory not found")

    masuk = (await db.execute(
        text(
            "SELECT barang_masuk_ref, jumlah_masuk, harga_beli, harga_jual, status, tanggal_masuk "
            "FROM koptumbuh.barang_masuk_produk "
            "WHERE produk_sample_id=:pid AND koperasi_ref=:ref "
            "ORDER BY tanggal_masuk DESC LIMIT 10"
        ),
        {"pid": produk_id, "ref": ref},
    )).fetchall()

    keluar = (await db.execute(
        text(
            "SELECT transaksi_sample_id, jumlah_keluar, harga, total_nilai, status_transaksi, tanggal_keluar "
            "FROM koptumbuh.barang_keluar_produk "
            "WHERE produk_sample_id=:pid AND koperasi_ref=:ref "
            "ORDER BY tanggal_keluar DESC LIMIT 10"
        ),
        {"pid": produk_id, "ref": ref},
    )).fetchall()

    return ApiResponse(data={
        "produk_sample_id": produk_id,
        "inventaris_ref": inv[0],
        "nama_produk": inv[1],
        "stok": float(inv[2] or 0),
        "barcode": inv[3],
        "lokasi_simpan": inv[4],
        "recent_masuk": [
            {
                "id": r[0],
                "qty": float(r[1] or 0),
                "harga_beli": float(r[2] or 0),
                "harga_jual": float(r[3] or 0),
                "status": r[4],
                "date": str(r[5]) if r[5] else None,
            }
            for r in masuk
        ],
        "recent_keluar": [
            {
                "transaksi_id": r[0],
                "qty": float(r[1] or 0),
                "harga": float(r[2] or 0),
                "total": float(r[3] or 0),
                "status": r[4],
                "date": str(r[5]) if r[5] else None,
            }
            for r in keluar
        ],
    })
