import json
import logging
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.models.koptumbuh import ParsingPesan, PesanMasuk, PenggunaKoptumbuh, NotifikasiLog
from app.services.whatsapp_service import whatsapp_service
from app.database import AsyncSessionLocal
import redis as redis_lib
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(bind=True, max_retries=3)
def dispatch_confirmation(self, parsing_id: str):
    """Format and send WhatsApp confirmation or error message."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_async_dispatch(parsing_id))
    finally:
        loop.close()


async def _async_dispatch(parsing_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ParsingPesan).where(ParsingPesan.parsing_id == parsing_id))
        parsing = result.scalar_one_or_none()
        if not parsing:
            return

        pesan_result = await db.execute(select(PesanMasuk).where(PesanMasuk.pesan_id == parsing.pesan_id))
        pesan = pesan_result.scalar_one()

        user_result = await db.execute(select(PenggunaKoptumbuh).where(PenggunaKoptumbuh.pengguna_id == pesan.pengguna_id))
        user = user_result.scalar_one()

        if parsing.status == "VALID":
            intent = parsing.detected_intent or (parsing.extracted_payload or {}).get("intent") or "RECORD_SALE"
            # Set Redis session state for confirmation
            redis_client.setex(
                f"session:{user.nomor_whatsapp}", 900,  # 15-minute TTL
                json.dumps({
                    "state": "AWAITING_CONFIRMATION",
                    "parsing_id": parsing_id,
                    "intent": intent,
                }),
            )
            message = _format_confirmation(parsing)
            logger.info("dispatch confirm: parsing_id=%s intent=%s to=%s", parsing_id, intent, user.nomor_whatsapp)
        else:
            message = _format_error(parsing)
            logger.info("dispatch error: parsing_id=%s to=%s", parsing_id, user.nomor_whatsapp)

        # Send via Evolution API
        result = await whatsapp_service.send_message(user.nomor_whatsapp, message)
        logger.info(
            "dispatch sent: parsing_id=%s success=%s",
            parsing_id,
            result.get("success"),
        )

        # Log notification
        notif = NotifikasiLog(
            koperasi_ref=pesan.koperasi_ref,
            pengguna_id=user.pengguna_id,
            channel="WHATSAPP",
            message_type="CONFIRMATION" if parsing.status == "VALID" else "ALERT",
            content=message,
            provider_message_id=result.get("message_id"),
            status="SENT" if result.get("success") else "FAILED",
        )
        db.add(notif)
        await db.commit()


def _format_confirmation(parsing: ParsingPesan) -> str:
    payload = parsing.extracted_payload or {}
    intent = parsing.detected_intent or payload.get("intent") or "RECORD_SALE"

    if intent == "ADJUST_STOCK":
        lines = [
            f"{i + 1}. {item['nama_produk']}  Δ {item['quantity']:+.0f} {item.get('unit', '')}"
            for i, item in enumerate(payload.get("resolved_items", []))
        ]
        return (
            "📋 *Konfirmasi Penyesuaian Stok*\n\n"
            + "\n".join(lines)
            + "\n\n_Harga & total dari DB (No AI Math)_\n\n"
            "Balas:\n"
            "✅ *YA* — Terapkan\n"
            "✏️ *UBAH* — Koreksi & kirim ulang\n"
            "❌ *BATAL* — Batalkan"
        )

    lines = []
    for i, item in enumerate(payload.get("resolved_items", [])):
        unit_price = item.get("unit_price", 0) or 0
        subtotal = item.get("subtotal", 0) or 0
        lines.append(
            f"{i + 1}. {item['nama_produk']}  {item['quantity']} x Rp {unit_price:,.0f} = Rp {subtotal:,.0f}"
        )

    payment = payload.get("payment_method", "Cash")
    header = "HUTANG" if payment == "Hutang" else "Konfirmasi Transaksi"
    due = f"\nJatuh Tempo: {payload.get('due_date', '-')}" if payment == "Hutang" else ""

    return (
        f"\U0001F4CB *{header}*\n"
        f"Pelanggan: {payload.get('customer_name', '-')}\n"
        f"Bayar: {payment}\n\n"
        + "\n".join(lines) +
        f"\n{'─' * 30}\n"
        f"*Total: Rp {payload.get('calculated_total', 0):,.0f}*{due}\n"
        f"_Harga & total dari DB (No AI Math)_\n\n"
        f"Balas:\n"
        f"✅ *YA* — Simpan\n"
        f"✏️ *UBAH* — Koreksi & kirim ulang\n"
        f"❌ *BATAL* — Batalkan"
    )


def _format_error(parsing: ParsingPesan) -> str:
    errors = parsing.validation_errors or []
    error_list = "\n".join([f"⚠️ {e}" for e in errors])
    return (
        f"⚠️ *Produk Tidak Ditemukan*\n\n"
        f"{error_list}\n\n"
        f"Silakan periksa nama produk atau hubungi admin.\n"
        f"Kirim ulang pesan dengan nama produk yang benar.\n\n"
        f"UBAH / BATAL"
    )


@celery_app.task
def send_morning_broadcast(koperasi_ref: str = None):
    """Daily 7 AM: Send price broadcast to all members."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_async_broadcast(koperasi_ref))
    finally:
        loop.close()


async def _async_broadcast(koperasi_ref: str = None):
    from sqlalchemy import text

    ref = koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PenggunaKoptumbuh).where(
                PenggunaKoptumbuh.koperasi_ref == ref,
                PenggunaKoptumbuh.status_aktif == True,
            )
        )
        users = result.scalars().all()

        price_rows = (
            await db.execute(
                text(
                    """
                    SELECT DISTINCT ON (p.produk_sample_id)
                           p.nama_produk, bm.harga_jual
                    FROM koptumbuh.produk_koperasi p
                    JOIN koptumbuh.barang_masuk_produk bm
                      ON bm.produk_sample_id = p.produk_sample_id
                     AND bm.koperasi_ref = p.koperasi_ref
                    WHERE p.koperasi_ref = :r
                      AND COALESCE(bm.status,'') NOT IN ('Rejected','Cancelled')
                      AND bm.harga_jual > 0
                    ORDER BY p.produk_sample_id, bm.tanggal_masuk DESC
                    LIMIT 8
                    """
                ),
                {"r": ref},
            )
        ).fetchall()

        if price_rows:
            price_lines = "\n".join(
                f"• {r[0]}: Rp {float(r[1]):,.0f}" for r in price_rows
            )
        else:
            price_lines = "• (harga belum tersedia — cek dashboard inventaris)"

        message = (
            "☀️ *Selamat Pagi!*\n"
            "Koperasi Tumbuh Bersama\n\n"
            "📋 Harga hari ini:\n"
            f"{price_lines}\n\n"
            "Balas: beli [produk] [jumlah] untuk catat transaksi.\n"
            "Gunakan Simpanan untuk pembayaran mudah!"
        )

        for user in users:
            await whatsapp_service.send_message(user.nomor_whatsapp, message)
