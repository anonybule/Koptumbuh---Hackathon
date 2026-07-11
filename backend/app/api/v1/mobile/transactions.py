import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment
from app.services.provenance import find_tx_by_client_id, insert_sumber, fetch_tx_summary

router = APIRouter(prefix="/mobile", tags=["mobile"])


class LineItem(BaseModel):
    produk_sample_id: str
    quantity: float = Field(gt=0)


class CreateTransactionBody(BaseModel):
    customer_name: str
    payment_method: str = "Cash"
    line_items: list[LineItem]
    tanggal_dibuat: datetime | None = None
    client_tx_id: str | None = None


@router.get("/transactions", response_model=ApiResponse)
async def list_transactions(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "koperasi_ref = :ref"
    params: dict = {"ref": ref, "offset": offset, "limit": limit}
    if date_from:
        where += " AND tanggal_dibuat::date >= :date_from"
        params["date_from"] = date_from
    if date_to:
        where += " AND tanggal_dibuat::date <= :date_to"
        params["date_to"] = date_to

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("offset", "limit")},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            f"""SELECT transaksi_sample_id, nama_pelanggan, total_pembayaran,
                       status_transaksi, metode_pembayaran, tanggal_dibuat
                FROM koptumbuh.transaksi_penjualan
                WHERE {where}
                ORDER BY tanggal_dibuat DESC
                OFFSET :offset LIMIT :limit"""
        ),
        params,
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


@router.get("/transactions/{tx_id}", response_model=ApiResponse)
async def get_transaction(
    tx_id: str,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    tx = (await db.execute(
        text(
            "SELECT transaksi_sample_id, nama_pelanggan, total_pembayaran, "
            "status_transaksi, metode_pembayaran, tanggal_dibuat "
            "FROM koptumbuh.transaksi_penjualan "
            "WHERE transaksi_sample_id=:id AND koperasi_ref=:ref"
        ),
        {"id": tx_id, "ref": ref},
    )).fetchone()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    items = (await db.execute(
        text(
            "SELECT produk_sample_id, nama_produk, jumlah_keluar, harga, total_nilai "
            "FROM koptumbuh.barang_keluar_produk "
            "WHERE transaksi_sample_id=:id AND koperasi_ref=:ref"
        ),
        {"id": tx_id, "ref": ref},
    )).fetchall()

    sumber = (await db.execute(
        text(
            "SELECT sumber, pesan_id, parsing_id, client_tx_id "
            "FROM koptumbuh.transaksi_sumber WHERE transaksi_sample_id=:id"
        ),
        {"id": tx_id},
    )).fetchone()

    return ApiResponse(data={
        "id": tx[0],
        "customer": tx[1],
        "total": float(tx[2] or 0),
        "status": tx[3],
        "payment_method": tx[4],
        "date": str(tx[5]) if tx[5] else None,
        "line_items": [
            {
                "produk_sample_id": i[0],
                "nama_produk": i[1],
                "quantity": float(i[2] or 0),
                "harga": float(i[3] or 0),
                "total": float(i[4] or 0),
            }
            for i in items
        ],
        "sumber": None if not sumber else {
            "channel": sumber[0],
            "pesan_id": str(sumber[1]) if sumber[1] else None,
            "parsing_id": str(sumber[2]) if sumber[2] else None,
            "client_tx_id": sumber[3],
        },
    })


@router.post("/transactions", response_model=ApiResponse)
async def create_transaction(
    body: CreateTransactionBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    if not body.line_items:
        raise HTTPException(status_code=400, detail="line_items required")

    ref = user["koperasi_ref"]
    client_tx_id = (idempotency_key or body.client_tx_id or "").strip() or None
    if client_tx_id:
        existing = await find_tx_by_client_id(db, ref, client_tx_id)
        if existing:
            summary = await fetch_tx_summary(db, existing, ref)
            return ApiResponse(data=summary or {"id": existing, "transaksi_sample_id": existing})

    payment = normalize_payment(body.payment_method)
    tx_status = "Unpaid" if payment == "Hutang" else "Paid"
    tx_id = f"TRX-{uuid.uuid4().hex[:12].upper()}"
    now = body.tanggal_dibuat or datetime.utcnow()
    resolved: list[dict] = []
    total = 0.0

    for item in body.line_items:
        price_row = (await db.execute(
            text(
                "SELECT harga_jual, nama_produk, kode_barcode FROM koptumbuh.barang_masuk_produk "
                "WHERE produk_sample_id=:pid AND koperasi_ref=:ref "
                "AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') "
                "ORDER BY tanggal_masuk DESC LIMIT 1"
            ),
            {"pid": item.produk_sample_id, "ref": ref},
        )).fetchone()
        if not price_row or price_row[0] is None:
            raise HTTPException(status_code=400, detail=f"No price for {item.produk_sample_id}")

        stock = (await db.execute(
            text(
                "SELECT stok FROM koptumbuh.inventaris_produk "
                "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
            ),
            {"pid": item.produk_sample_id, "ref": ref},
        )).scalar()
        if stock is None or float(stock) < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.produk_sample_id}",
            )

        harga = float(price_row[0])
        line_total = harga * item.quantity
        total += line_total
        resolved.append({
            "produk_sample_id": item.produk_sample_id,
            "quantity": item.quantity,
            "harga": harga,
            "total": line_total,
            "nama_produk": price_row[1],
            "kode_barcode": price_row[2],
        })

    await db.execute(
        text(
            "INSERT INTO koptumbuh.transaksi_penjualan "
            "(transaksi_sample_id, koperasi_ref, nama_pelanggan, tanggal_dibuat, "
            " total_pembayaran, status_transaksi, metode_pembayaran) "
            "VALUES (:id, :ref, :nama, :tgl, :total, :st, :pay)"
        ),
        {
            "id": tx_id,
            "ref": ref,
            "nama": body.customer_name,
            "tgl": now,
            "total": total,
            "st": tx_status,
            "pay": payment,
        },
    )

    for r in resolved:
        await db.execute(
            text(
                "INSERT INTO koptumbuh.barang_keluar_produk "
                "(transaksi_sample_id, produk_sample_id, koperasi_ref, kode_barcode, "
                " tanggal_keluar, nama_produk, jumlah_keluar, harga, total_nilai, status_transaksi) "
                "VALUES (:tx, :pid, :ref, :barcode, :tgl, :nama, :qty, :harga, :total, :st)"
            ),
            {
                "tx": tx_id,
                "pid": r["produk_sample_id"],
                "ref": ref,
                "barcode": r["kode_barcode"],
                "tgl": now,
                "nama": r["nama_produk"],
                "qty": r["quantity"],
                "harga": r["harga"],
                "total": r["total"],
                "st": tx_status,
            },
        )
        await db.execute(
            text(
                "UPDATE koptumbuh.inventaris_produk "
                "SET stok = stok - :qty, diperbarui_pada = NOW() "
                "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
            ),
            {"qty": r["quantity"], "pid": r["produk_sample_id"], "ref": ref},
        )

    await insert_sumber(
        db,
        transaksi_sample_id=tx_id,
        koperasi_ref=ref,
        sumber="MOBILE",
        pengguna_id=user.get("pengguna_id"),
        client_tx_id=client_tx_id,
    )
    await db.commit()
    return ApiResponse(data={
        "id": tx_id,
        "customer": body.customer_name,
        "total": total,
        "payment_method": payment,
        "line_items": resolved,
        "client_tx_id": client_tx_id,
    })
