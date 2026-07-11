import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-suppliers"])


@router.get("/suppliers", response_model=ApiResponse)
async def list_suppliers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    active_only: bool = True,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "koperasi_ref=:r" + (" AND status_aktif=true" if active_only else "")
    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.pemasok_koptumbuh WHERE {where}"), {"r": ref})
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT pemasok_id, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term, status_aktif "
            f"FROM koptumbuh.pemasok_koptumbuh WHERE {where} ORDER BY nama_pemasok "
            f"OFFSET :off LIMIT :lim"
        ),
        {"r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "name": r[1],
                "phone": r[2],
                "alamat": r[3],
                "lead_time": float(r[4]) if r[4] is not None else 0,
                "payment": r[5],
                "status_aktif": r[6],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/suppliers", response_model=ApiResponse)
async def create_supplier(body: dict, user: dict = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    name = body.get("nama_pemasok") or body.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="nama_pemasok is required")
    sid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO koptumbuh.pemasok_koptumbuh "
            "(pemasok_id, koperasi_ref, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term, status_aktif) "
            "VALUES (:id, :r, :n, :hp, :alamat, :lt, :pt, true)"
        ),
        {
            "id": sid,
            "r": user["koperasi_ref"],
            "n": name,
            "hp": body.get("nomor_hp") or body.get("phone"),
            "alamat": body.get("alamat"),
            "lt": body.get("lead_time_hari") or body.get("lead_time"),
            "pt": body.get("payment_term") or body.get("payment"),
        },
    )
    await db.commit()
    return ApiResponse(data={"id": sid, "nama_pemasok": name})


@router.get("/suppliers/{id}", response_model=ApiResponse)
async def supplier_detail(id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT pemasok_id, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term, status_aktif "
            "FROM koptumbuh.pemasok_koptumbuh WHERE pemasok_id=:id AND koperasi_ref=:r"
        ),
        {"id": id, "r": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Prefer scorecard view; fall back to simple counts
    try:
        score = await db.execute(
            text(
                "SELECT lead_time_aktual_rata, produk_disuplai, total_pengiriman, persentase_tepat_waktu "
                "FROM koptumbuh.v_skor_pemasok WHERE pemasok_id=:id AND koperasi_ref=:r"
            ),
            {"id": id, "r": ref},
        )
        sc = score.fetchone()
    except Exception:
        await db.rollback()
        sc = None

    orders = await db.execute(
        text(
            "SELECT barang_masuk_ref, produk_sample_id, nama_produk, jumlah_masuk, harga_beli, total_biaya, "
            "tanggal_masuk, status FROM koptumbuh.barang_masuk_produk "
            "WHERE koperasi_ref=:r AND pemasok_id=:id ORDER BY tanggal_masuk DESC NULLS LAST LIMIT 20"
        ),
        {"r": ref, "id": id},
    )
    try:
        order_rows = orders.fetchall()
    except Exception:
        await db.rollback()
        order_rows = []

    products = await db.execute(
        text(
            "SELECT DISTINCT produk_sample_id, nama_produk FROM koptumbuh.barang_masuk_produk "
            "WHERE koperasi_ref=:r AND pemasok_id=:id"
        ),
        {"r": ref, "id": id},
    )
    try:
        product_rows = products.fetchall()
    except Exception:
        await db.rollback()
        product_rows = []

    return ApiResponse(
        data={
            "id": str(row[0]),
            "name": row[1],
            "phone": row[2],
            "alamat": row[3],
            "lead_time": float(row[4]) if row[4] is not None else 0,
            "payment": row[5],
            "status_aktif": row[6],
            "scorecard": {
                "lead_time_aktual_rata": float(sc[0] or 0) if sc else None,
                "produk_disuplai": sc[1] if sc else len(product_rows),
                "total_pengiriman": sc[2] if sc else len(order_rows),
                "persentase_tepat_waktu": float(sc[3] or 0) if sc and sc[3] is not None else None,
            },
            "products": [{"produk_sample_id": p[0], "nama_produk": p[1]} for p in product_rows],
            "recent_orders": [
                {
                    "barang_masuk_ref": o[0],
                    "produk_sample_id": o[1],
                    "nama_produk": o[2],
                    "qty": float(o[3] or 0),
                    "harga_beli": float(o[4] or 0),
                    "total": float(o[5] or 0),
                    "date": str(o[6]) if o[6] else None,
                    "status": o[7],
                }
                for o in order_rows
            ],
        }
    )


@router.patch("/suppliers/{id}", response_model=ApiResponse)
async def update_supplier(
    id: str,
    body: dict,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    exists = await db.execute(
        text("SELECT 1 FROM koptumbuh.pemasok_koptumbuh WHERE pemasok_id=:id AND koperasi_ref=:r"),
        {"id": id, "r": ref},
    )
    if not exists.scalar():
        raise HTTPException(status_code=404, detail="Supplier not found")

    fields = []
    params: dict = {"id": id, "r": ref}
    mapping = {
        "nama_pemasok": "nama_pemasok",
        "name": "nama_pemasok",
        "nomor_hp": "nomor_hp",
        "phone": "nomor_hp",
        "alamat": "alamat",
        "lead_time_hari": "lead_time_hari",
        "lead_time": "lead_time_hari",
        "payment_term": "payment_term",
        "payment": "payment_term",
        "status_aktif": "status_aktif",
    }
    for key, col in mapping.items():
        if key in body and col not in params:
            fields.append(f"{col}=:{col}")
            params[col] = body[key]
    if not fields:
        raise HTTPException(status_code=422, detail="No updatable fields provided")
    fields.append("updated_at=NOW()")
    await db.execute(
        text(f"UPDATE koptumbuh.pemasok_koptumbuh SET {', '.join(fields)} WHERE pemasok_id=:id AND koperasi_ref=:r"),
        params,
    )
    await db.commit()
    return ApiResponse(data={"id": id, "updated": True})


@router.get("/suppliers/{id}/orders", response_model=ApiResponse)
async def supplier_orders(
    id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    try:
        total = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.barang_masuk_produk "
                    "WHERE koperasi_ref=:r AND pemasok_id=:id"
                ),
                {"r": ref, "id": id},
            )
        ).scalar() or 0
        result = await db.execute(
            text(
                "SELECT barang_masuk_ref, produk_sample_id, nama_produk, jumlah_masuk, harga_beli, "
                "total_biaya, tanggal_masuk, status "
                "FROM koptumbuh.barang_masuk_produk WHERE koperasi_ref=:r AND pemasok_id=:id "
                "ORDER BY tanggal_masuk DESC NULLS LAST OFFSET :off LIMIT :lim"
            ),
            {"r": ref, "id": id, "off": offset, "lim": limit},
        )
        rows = result.fetchall()
    except Exception:
        await db.rollback()
        total = 0
        rows = []

    return ApiResponse(
        data=[
            {
                "barang_masuk_ref": r[0],
                "produk_sample_id": r[1],
                "nama_produk": r[2],
                "qty": float(r[3] or 0),
                "harga_beli": float(r[4] or 0),
                "total": float(r[5] or 0),
                "date": str(r[6]) if r[6] else None,
                "status": r[7],
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/restock-plan", response_model=ApiResponse)
async def restock_plan(user: dict = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    """Products needing restock: stock, ADS, days left, suggested qty, preferred supplier."""
    from app.workers.supply_chain import compute_restock_plan

    ref = user["koperasi_ref"]
    plan = await compute_restock_plan(db, ref)
    return ApiResponse(data=plan)


@router.get("/purchase-history", response_model=ApiResponse)
async def purchase_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    pemasok_id: str | None = None,
    produk_sample_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["bm.koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if pemasok_id:
        where.append("bm.pemasok_id=:sid")
        params["sid"] = pemasok_id
    if produk_sample_id:
        where.append("bm.produk_sample_id=:pid")
        params["pid"] = produk_sample_id
    if date_from:
        where.append("COALESCE(bm.tanggal_masuk, bm.dibuat_pada)::date >= :df")
        params["df"] = date_from
    if date_to:
        where.append("COALESCE(bm.tanggal_masuk, bm.dibuat_pada)::date <= :dt")
        params["dt"] = date_to
    clause = " AND ".join(where)

    try:
        total = (
            await db.execute(
                text(f"SELECT COUNT(*) FROM koptumbuh.barang_masuk_produk bm WHERE {clause}"),
                params,
            )
        ).scalar() or 0
        result = await db.execute(
            text(
                f"SELECT bm.barang_masuk_ref, bm.produk_sample_id, bm.nama_produk, bm.jumlah_masuk, "
                f"bm.harga_beli, bm.harga_jual, bm.total_biaya, bm.tanggal_masuk, bm.status, "
                f"bm.pemasok_id, s.nama_pemasok "
                f"FROM koptumbuh.barang_masuk_produk bm "
                f"LEFT JOIN koptumbuh.pemasok_koptumbuh s ON s.pemasok_id=bm.pemasok_id "
                f"WHERE {clause} ORDER BY bm.tanggal_masuk DESC NULLS LAST OFFSET :off LIMIT :lim"
            ),
            params,
        )
        rows = result.fetchall()
    except Exception:
        await db.rollback()
        # Fallback without pemasok_id column
        where2 = [w for w in where if "pemasok_id" not in w]
        clause2 = " AND ".join(where2) if where2 else "bm.koperasi_ref=:r"
        params2 = {k: v for k, v in params.items() if k != "sid"}
        total = (
            await db.execute(
                text(f"SELECT COUNT(*) FROM koptumbuh.barang_masuk_produk bm WHERE {clause2}"),
                params2,
            )
        ).scalar() or 0
        result = await db.execute(
            text(
                f"SELECT bm.barang_masuk_ref, bm.produk_sample_id, bm.nama_produk, bm.jumlah_masuk, "
                f"bm.harga_beli, bm.harga_jual, bm.total_biaya, bm.tanggal_masuk, bm.status, "
                f"NULL::uuid, NULL::text "
                f"FROM koptumbuh.barang_masuk_produk bm "
                f"WHERE {clause2} ORDER BY bm.tanggal_masuk DESC NULLS LAST OFFSET :off LIMIT :lim"
            ),
            params2,
        )
        rows = result.fetchall()

    return ApiResponse(
        data=[
            {
                "barang_masuk_ref": r[0],
                "produk_sample_id": r[1],
                "nama_produk": r[2],
                "qty": float(r[3] or 0),
                "harga_beli": float(r[4] or 0),
                "harga_jual": float(r[5] or 0) if r[5] is not None else None,
                "total": float(r[6] or 0),
                "date": str(r[7]) if r[7] else None,
                "status": r[8],
                "pemasok_id": str(r[9]) if r[9] else None,
                "supplier": r[10],
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/purchase-history", response_model=ApiResponse)
async def record_purchase(body: dict, user: dict = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    """Record purchase/restock: barang_masuk + update inventaris."""
    ref = user["koperasi_ref"]
    produk_id = body.get("produk_sample_id")
    qty = float(body.get("jumlah_masuk") or body.get("qty") or 0)
    buy = float(body.get("harga_beli") or 0)
    sell = float(body.get("harga_jual") or 0)
    pemasok_id = body.get("pemasok_id")
    name = body.get("nama_produk")
    if not produk_id or qty <= 0:
        raise HTTPException(status_code=422, detail="produk_sample_id and positive jumlah_masuk required")

    prod = await db.execute(
        text("SELECT nama_produk FROM koptumbuh.produk_koperasi WHERE produk_sample_id=:p AND koperasi_ref=:r"),
        {"p": produk_id, "r": ref},
    )
    prow = prod.fetchone()
    if not prow:
        raise HTTPException(status_code=404, detail="Product not found")
    name = name or prow[0]
    bm_ref = f"BM-{uuid.uuid4().hex[:12].upper()}"

    try:
        await db.execute(
            text(
                "INSERT INTO koptumbuh.barang_masuk_produk "
                "(barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk, jumlah_masuk, jumlah_tersedia, "
                "harga_beli, harga_jual, total_biaya, status, tanggal_masuk, pemasok_id) "
                "VALUES (:bm, :p, :r, :n, :q, :q, :buy, :sell, :cost, 'Diterima', NOW(), :sid)"
            ),
            {
                "bm": bm_ref,
                "p": produk_id,
                "r": ref,
                "n": name,
                "q": qty,
                "buy": buy,
                "sell": sell,
                "cost": qty * buy,
                "sid": pemasok_id,
            },
        )
    except Exception:
        await db.rollback()
        await db.execute(
            text(
                "INSERT INTO koptumbuh.barang_masuk_produk "
                "(barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk, jumlah_masuk, jumlah_tersedia, "
                "harga_beli, harga_jual, total_biaya, status, tanggal_masuk, keterangan) "
                "VALUES (:bm, :p, :r, :n, :q, :q, :buy, :sell, :cost, 'Diterima', NOW(), :ket)"
            ),
            {
                "bm": bm_ref,
                "p": produk_id,
                "r": ref,
                "n": name,
                "q": qty,
                "buy": buy,
                "sell": sell,
                "cost": qty * buy,
                "ket": f"pemasok_id={pemasok_id}" if pemasok_id else None,
            },
        )

    await db.execute(
        text(
            "UPDATE koptumbuh.inventaris_produk SET stok=COALESCE(stok,0)+:q, diperbarui_pada=NOW() "
            "WHERE produk_sample_id=:p AND koperasi_ref=:r"
        ),
        {"q": qty, "p": produk_id, "r": ref},
    )
    await db.commit()
    return ApiResponse(data={"barang_masuk_ref": bm_ref, "produk_sample_id": produk_id, "qty": qty})
