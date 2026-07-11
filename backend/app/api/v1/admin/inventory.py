import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-inventory"])


@router.get("/inventory", response_model=ApiResponse)
async def list_inventory(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    q: str | None = None,
    low_stock_only: bool = False,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["i.koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if q:
        where.append("(i.nama_produk ILIKE :q OR i.kode_barcode ILIKE :q OR i.produk_sample_id ILIKE :q)")
        params["q"] = f"%{q}%"
    if low_stock_only:
        where.append("i.stok < 5")
    clause = " AND ".join(where)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.inventaris_produk i WHERE {clause}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT i.produk_sample_id, i.nama_produk, i.stok, i.kode_barcode, i.lokasi_simpan, i.inventaris_ref, "
            f"(SELECT bm.harga_jual FROM koptumbuh.barang_masuk_produk bm "
            f" WHERE bm.produk_sample_id = i.produk_sample_id AND bm.koperasi_ref = i.koperasi_ref "
            f"   AND bm.harga_jual IS NOT NULL AND bm.harga_jual > 0 "
            f" ORDER BY bm.tanggal_masuk DESC NULLS LAST LIMIT 1) AS harga_jual "
            f"FROM koptumbuh.inventaris_produk i WHERE {clause} ORDER BY i.stok ASC OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "name": r[1],
                "stock": float(r[2] or 0),
                "barcode": r[3],
                "lokasi_simpan": r[4],
                "inventaris_ref": r[5],
                "harga_jual": float(r[6] or 0),
                "low_stock": float(r[2] or 0) < 5,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/inventory/adjustments", response_model=ApiResponse)
async def list_adjustments(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (
        await db.execute(
            text("SELECT COUNT(*) FROM koptumbuh.penyesuaian_stok WHERE koperasi_ref=:r"),
            {"r": ref},
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            "SELECT p.penyesuaian_id, p.produk_sample_id, COALESCE(i.nama_produk, pr.nama_produk), "
            "p.quantity_delta, p.reason, p.pengguna_id, u.nama, p.source_message_id, p.created_at "
            "FROM koptumbuh.penyesuaian_stok p "
            "LEFT JOIN koptumbuh.inventaris_produk i ON i.produk_sample_id=p.produk_sample_id AND i.koperasi_ref=p.koperasi_ref "
            "LEFT JOIN koptumbuh.produk_koperasi pr ON pr.produk_sample_id=p.produk_sample_id "
            "LEFT JOIN koptumbuh.pengguna_koptumbuh u ON u.pengguna_id=p.pengguna_id "
            "WHERE p.koperasi_ref=:r ORDER BY p.created_at DESC OFFSET :off LIMIT :lim"
        ),
        {"r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "produk_sample_id": r[1],
                "nama_produk": r[2],
                "quantity_delta": float(r[3] or 0),
                "reason": r[4],
                "pengguna_id": str(r[5]) if r[5] else None,
                "pengguna_nama": r[6],
                "source_message_id": str(r[7]) if r[7] else None,
                "created_at": str(r[8]) if r[8] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/inventory/adjustments", response_model=ApiResponse)
async def create_adjustment(
    body: dict,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    produk_id = body.get("produk_sample_id")
    delta = float(body.get("quantity_delta", 0))
    reason = body.get("reason") or body.get("alasan")
    if not produk_id or reason is None or reason == "":
        raise HTTPException(status_code=422, detail="produk_sample_id and reason are required")
    if delta == 0:
        raise HTTPException(status_code=422, detail="quantity_delta must be non-zero")

    exists = await db.execute(
        text("SELECT 1 FROM koptumbuh.produk_koperasi WHERE produk_sample_id=:p AND koperasi_ref=:r"),
        {"p": produk_id, "r": ref},
    )
    if not exists.scalar():
        raise HTTPException(status_code=404, detail="Product not found")

    adj_id = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO koptumbuh.penyesuaian_stok "
            "(penyesuaian_id, koperasi_ref, produk_sample_id, pengguna_id, quantity_delta, reason) "
            "VALUES (:id, :r, :p, :u, :d, :reason)"
        ),
        {"id": adj_id, "r": ref, "p": produk_id, "u": user["pengguna_id"], "d": delta, "reason": reason},
    )
    await db.execute(
        text(
            "UPDATE koptumbuh.inventaris_produk SET stok = COALESCE(stok,0) + :d, diperbarui_pada=NOW() "
            "WHERE produk_sample_id=:p AND koperasi_ref=:r"
        ),
        {"d": delta, "p": produk_id, "r": ref},
    )
    await db.commit()
    return ApiResponse(data={"penyesuaian_id": adj_id, "produk_sample_id": produk_id, "quantity_delta": delta})


@router.post("/inventory/add", response_model=ApiResponse)
async def add_product(body: dict, user: dict = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    """Add a new product with initial stock via barang_masuk."""
    ref = user["koperasi_ref"]
    pid = f"PROD-{uuid.uuid4().hex[:12].upper()}"
    bm_ref = f"BM-{uuid.uuid4().hex[:12].upper()}"
    inv_ref = f"INV-{uuid.uuid4().hex[:12].upper()}"
    name = body.get("nama_produk", "")
    qty = float(body.get("jumlah_masuk", 0))
    buy = float(body.get("harga_beli", 0))
    sell = float(body.get("harga_jual", 0))
    barcode = body.get("kode_barcode")
    if not name:
        raise HTTPException(status_code=422, detail="nama_produk is required")

    await db.execute(
        text(
            "INSERT INTO koptumbuh.produk_koperasi (produk_sample_id, koperasi_ref, nama_produk, kode_barcode, unit) "
            "VALUES (:p, :r, :n, :b, 'Pcs')"
        ),
        {"p": pid, "r": ref, "n": name, "b": barcode},
    )
    await db.execute(
        text(
            "INSERT INTO koptumbuh.barang_masuk_produk "
            "(barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk, jumlah_masuk, jumlah_tersedia, "
            "harga_beli, harga_jual, total_biaya, status, tanggal_masuk) "
            "VALUES (:bm, :p, :r, :n, :q, :q, :buy, :sell, :cost, 'Diterima', NOW())"
        ),
        {"bm": bm_ref, "p": pid, "r": ref, "n": name, "q": qty, "buy": buy, "sell": sell, "cost": qty * buy},
    )
    await db.execute(
        text(
            "INSERT INTO koptumbuh.inventaris_produk "
            "(inventaris_ref, produk_sample_id, koperasi_ref, nama_produk, stok, kode_barcode) "
            "VALUES (:i, :p, :r, :n, :q, :b)"
        ),
        {"i": inv_ref, "p": pid, "r": ref, "n": name, "q": qty, "b": barcode},
    )
    await db.commit()
    return ApiResponse(data={"produk_sample_id": pid, "nama_produk": name})


@router.get("/inventory/{id}", response_model=ApiResponse)
async def inventory_detail(id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT i.produk_sample_id, i.nama_produk, i.stok, i.kode_barcode, i.lokasi_simpan, "
            "i.inventaris_ref, i.tanggal_masuk_gudang, p.unit, p.is_subsidi "
            "FROM koptumbuh.inventaris_produk i "
            "LEFT JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id=i.produk_sample_id "
            "WHERE i.produk_sample_id=:id AND i.koperasi_ref=:r"
        ),
        {"id": id, "r": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found in inventory")

    chart = await db.execute(
        text(
            "SELECT tanggal, tipe, qty FROM ("
            "  SELECT COALESCE(tanggal_masuk, dibuat_pada) AS tanggal, 'MASUK' AS tipe, jumlah_masuk AS qty "
            "  FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id=:id AND koperasi_ref=:r "
            "  UNION ALL "
            "  SELECT COALESCE(tanggal_keluar, dibuat_pada), 'KELUAR', jumlah_keluar "
            "  FROM koptumbuh.barang_keluar_produk WHERE produk_sample_id=:id AND koperasi_ref=:r "
            "  UNION ALL "
            "  SELECT created_at, 'ADJUST', quantity_delta "
            "  FROM koptumbuh.penyesuaian_stok WHERE produk_sample_id=:id AND koperasi_ref=:r"
            ") m ORDER BY tanggal DESC LIMIT 60"
        ),
        {"id": id, "r": ref},
    )
    return ApiResponse(
        data={
            "id": row[0],
            "name": row[1],
            "stock": float(row[2] or 0),
            "barcode": row[3],
            "lokasi_simpan": row[4],
            "inventaris_ref": row[5],
            "tanggal_masuk_gudang": str(row[6]) if row[6] else None,
            "unit": row[7],
            "is_subsidi": row[8],
            "low_stock": float(row[2] or 0) < 5,
            "chart": [
                {"date": str(c[0]) if c[0] else None, "type": c[1], "qty": float(c[2] or 0)}
                for c in chart.fetchall()
            ],
        }
    )


@router.get("/inventory/{id}/movements", response_model=ApiResponse)
async def inventory_movements(
    id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    count = await db.execute(
        text(
            "SELECT ("
            "  (SELECT COUNT(*) FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id=:id AND koperasi_ref=:r) + "
            "  (SELECT COUNT(*) FROM koptumbuh.barang_keluar_produk WHERE produk_sample_id=:id AND koperasi_ref=:r) + "
            "  (SELECT COUNT(*) FROM koptumbuh.penyesuaian_stok WHERE produk_sample_id=:id AND koperasi_ref=:r)"
            ")"
        ),
        {"id": id, "r": ref},
    )
    total = count.scalar() or 0
    result = await db.execute(
        text(
            "SELECT * FROM ("
            "  SELECT COALESCE(tanggal_masuk, dibuat_pada) AS tanggal, 'MASUK' AS tipe, "
            "  barang_masuk_ref AS ref_id, jumlah_masuk AS qty, harga_beli AS harga, status AS status "
            "  FROM koptumbuh.barang_masuk_produk WHERE produk_sample_id=:id AND koperasi_ref=:r "
            "  UNION ALL "
            "  SELECT COALESCE(tanggal_keluar, dibuat_pada), 'KELUAR', transaksi_sample_id, "
            "  jumlah_keluar, harga, status_transaksi "
            "  FROM koptumbuh.barang_keluar_produk WHERE produk_sample_id=:id AND koperasi_ref=:r "
            "  UNION ALL "
            "  SELECT created_at, 'ADJUST', penyesuaian_id::text, quantity_delta, NULL, reason "
            "  FROM koptumbuh.penyesuaian_stok WHERE produk_sample_id=:id AND koperasi_ref=:r"
            ") m ORDER BY tanggal DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        {"id": id, "r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "date": str(r[0]) if r[0] else None,
                "type": r[1],
                "ref_id": r[2],
                "qty": float(r[3] or 0),
                "harga": float(r[4]) if r[4] is not None else None,
                "status": r[5],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )
