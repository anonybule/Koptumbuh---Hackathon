"""In-store POS — Path B fallback with idempotency + provenance."""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import require_operator
from app.schemas.common import ApiResponse
from app.services.normalize import normalize_payment
from app.services.provenance import find_tx_by_client_id, insert_sumber, fetch_tx_summary

router = APIRouter(prefix="/admin", tags=["admin-pos"])


class LineItem(BaseModel):
    produk_sample_id: str
    quantity: float = Field(gt=0)


class CreatePosTransactionBody(BaseModel):
    customer_name: str
    payment_method: str = "Cash"
    line_items: list[LineItem]
    tanggal_dibuat: datetime | None = None
    client_tx_id: str | None = None


@router.post("/pos/transactions", response_model=ApiResponse)
async def create_pos_transaction(
    body: CreatePosTransactionBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    """In-store POS sale — same stock/price logic as mobile POST /transactions."""
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
        price_row = (
            await db.execute(
                text(
                    "SELECT harga_jual, nama_produk, kode_barcode FROM koptumbuh.barang_masuk_produk "
                    "WHERE produk_sample_id=:pid AND koperasi_ref=:ref "
                    "AND COALESCE(status,'') NOT IN ('Rejected','Cancelled') "
                    "ORDER BY tanggal_masuk DESC LIMIT 1"
                ),
                {"pid": item.produk_sample_id, "ref": ref},
            )
        ).fetchone()
        if not price_row or price_row[0] is None:
            raise HTTPException(status_code=400, detail=f"No price for {item.produk_sample_id}")

        stock = (
            await db.execute(
                text(
                    "SELECT stok FROM koptumbuh.inventaris_produk "
                    "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
                ),
                {"pid": item.produk_sample_id, "ref": ref},
            )
        ).scalar()
        if stock is None or float(stock) < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {item.produk_sample_id}",
            )

        harga = float(price_row[0])
        line_total = harga * item.quantity
        total += line_total
        resolved.append(
            {
                "produk_sample_id": item.produk_sample_id,
                "quantity": item.quantity,
                "harga": harga,
                "total": line_total,
                "nama_produk": price_row[1],
                "kode_barcode": price_row[2],
            }
        )

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
        sumber="POS",
        pengguna_id=user.get("pengguna_id"),
        client_tx_id=client_tx_id,
    )
    await db.commit()
    return ApiResponse(
        data={
            "id": tx_id,
            "transaksi_sample_id": tx_id,
            "customer": body.customer_name,
            "total": total,
            "payment_method": payment,
            "line_items": resolved,
            "client_tx_id": client_tx_id,
        }
    )
