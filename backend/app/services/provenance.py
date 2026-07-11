"""Link ledger rows to WhatsApp/POS/mobile source + offline idempotency."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def find_tx_by_client_id(
    db: AsyncSession, koperasi_ref: str, client_tx_id: str
) -> str | None:
    if not client_tx_id:
        return None
    row = (
        await db.execute(
            text(
                "SELECT transaksi_sample_id FROM koptumbuh.transaksi_sumber "
                "WHERE koperasi_ref=:r AND client_tx_id=:c LIMIT 1"
            ),
            {"r": koperasi_ref, "c": client_tx_id},
        )
    ).fetchone()
    return row[0] if row else None


async def insert_sumber(
    db: AsyncSession,
    *,
    transaksi_sample_id: str,
    koperasi_ref: str,
    sumber: str,
    pesan_id=None,
    parsing_id=None,
    pengguna_id=None,
    client_tx_id: str | None = None,
) -> None:
    await db.execute(
        text(
            "INSERT INTO koptumbuh.transaksi_sumber "
            "(transaksi_sample_id, koperasi_ref, sumber, pesan_id, parsing_id, pengguna_id, client_tx_id) "
            "VALUES (:tx, :r, :sumber, :pesan, :parsing, :user, :client) "
            "ON CONFLICT (transaksi_sample_id) DO NOTHING"
        ),
        {
            "tx": transaksi_sample_id,
            "r": koperasi_ref,
            "sumber": sumber,
            "pesan": pesan_id,
            "parsing": parsing_id,
            "user": pengguna_id,
            "client": client_tx_id or None,
        },
    )


async def fetch_tx_summary(db: AsyncSession, tx_id: str, koperasi_ref: str) -> dict | None:
    row = (
        await db.execute(
            text(
                "SELECT transaksi_sample_id, nama_pelanggan, total_pembayaran, "
                "status_transaksi, metode_pembayaran, tanggal_dibuat "
                "FROM koptumbuh.transaksi_penjualan "
                "WHERE transaksi_sample_id=:id AND koperasi_ref=:r"
            ),
            {"id": tx_id, "r": koperasi_ref},
        )
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "transaksi_sample_id": row[0],
        "customer": row[1],
        "total": float(row[2] or 0),
        "status": row[3],
        "payment_method": row[4],
        "date": str(row[5]) if row[5] else None,
        "idempotent_replay": True,
    }
