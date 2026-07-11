import json
from datetime import datetime
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.koptumbuh import (
    PesanMasuk, ParsingPesan, KonfirmasiPengguna,
    PenggunaKoptumbuh, RelasiTransaksiPihak,
)
from app.models.transactions import TransaksiPenjualan
from app.models.products import BarangKeluarProduk, InventarisProduk
from app.services.whatsapp_service import whatsapp_service
from app.services.normalize import normalize_payment, normalize_unit
import redis as redis_lib
from app.config import settings

redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def handle_confirmation_reply(pesan: PesanMasuk, db: AsyncSession):
    """Detect and handle YA/UBAH/BATAL replies to pending confirmations."""
    reply = (pesan.raw_text or "").strip().upper()

    # Get user
    user_result = await db.execute(
        select(PenggunaKoptumbuh).where(PenggunaKoptumbuh.pengguna_id == pesan.pengguna_id)
    )
    user = user_result.scalar_one()

    # Check for active confirmation session
    session_data = redis_client.get(f"session:{user.nomor_whatsapp}")
    if not session_data:
        return False  # No active session, treat as new message

    session = json.loads(session_data)
    parsing_result = await db.execute(
        select(ParsingPesan).where(ParsingPesan.parsing_id == session["parsing_id"])
    )
    parsing = parsing_result.scalar_one_or_none()
    if not parsing:
        return False

    if reply == "YA":
        intent = (
            session.get("intent")
            or parsing.detected_intent
            or (parsing.extracted_payload or {}).get("intent")
            or "RECORD_SALE"
        )
        try:
            if intent == "ADJUST_STOCK":
                await commit_stock_adjustment(parsing, pesan, user, db)
                redis_client.delete(f"session:{user.nomor_whatsapp}")
                await whatsapp_service.send_message(
                    user.nomor_whatsapp,
                    "✅ Penyesuaian stok berhasil diterapkan.",
                )
                return True
            await commit_transaction(parsing, pesan, user, db)
        except ValueError as e:
            await db.rollback()
            await whatsapp_service.send_message(
                user.nomor_whatsapp,
                f"❌ Gagal menyimpan: {e}\n\nBalas *UBAH* untuk kirim ulang, atau *BATAL* untuk batalkan.",
            )
            return True
        redis_client.delete(f"session:{user.nomor_whatsapp}")
        await whatsapp_service.send_message(
            user.nomor_whatsapp,
            f"✅ Transaksi berhasil disimpan!\nTotal: Rp {parsing.extracted_payload.get('calculated_total', 0):,.0f}"
        )
        return True

    elif reply == "UBAH":
        parsing.status = "SUPERSEDED"
        await db.commit()
        redis_client.delete(f"session:{user.nomor_whatsapp}")
        await whatsapp_service.send_message(
            user.nomor_whatsapp,
            "Draf dibatalkan. Silakan kirim ulang pesan dengan format yang benar."
        )
        return True

    elif reply == "BATAL":
        pesan.status = "CANCELLED"
        await db.commit()
        redis_client.delete(f"session:{user.nomor_whatsapp}")
        await whatsapp_service.send_message(
            user.nomor_whatsapp,
            "❌ Transaksi dibatalkan. Tidak ada data yang disimpan."
        )
        return True

    return False


async def commit_stock_adjustment(
    parsing: ParsingPesan, pesan: PesanMasuk, user: PenggunaKoptumbuh, db: AsyncSession
):
    """Apply inventaris delta after YA on ADJUST_STOCK confirmation."""
    from app.models.koptumbuh import PenyesuaianStok

    payload = parsing.extracted_payload or {}
    koperasi_ref = pesan.koperasi_ref
    reason = payload.get("customer_name") or "Adjustment via WhatsApp"

    for item in payload.get("resolved_items", []):
        delta = float(item.get("quantity") or 0)
        inv_result = await db.execute(
            select(InventarisProduk).where(
                InventarisProduk.koperasi_ref == koperasi_ref,
                InventarisProduk.produk_sample_id == item["produk_sample_id"],
            )
        )
        inv = inv_result.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Inventory record not found for {item.get('nama_produk')}")
        inv.stok = float(inv.stok or 0) + delta

        adj = PenyesuaianStok(
            koperasi_ref=koperasi_ref,
            produk_sample_id=item["produk_sample_id"],
            pengguna_id=user.pengguna_id,
            quantity_delta=delta,
            reason=f"Adjustment via WhatsApp: {reason}",
            source_message_id=pesan.pesan_id,
        )
        db.add(adj)

    konfirmasi = KonfirmasiPengguna(
        pesan_id=pesan.pesan_id,
        parsing_id=parsing.parsing_id,
        pengguna_id=user.pengguna_id,
        keputusan="YA",
    )
    db.add(konfirmasi)
    parsing.status = "VALID"
    pesan.status = "CONFIRMED"
    pesan.processed_at = datetime.utcnow()
    await db.commit()


async def commit_transaction(parsing: ParsingPesan, pesan: PesanMasuk, user: PenggunaKoptumbuh, db: AsyncSession):
    """Atomic transaction commit — YA handler."""
    import uuid

    payload = parsing.extracted_payload or {}
    koperasi_ref = pesan.koperasi_ref
    now = datetime.utcnow()
    tx_id = f"TRX-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    payment = normalize_payment(payload.get("payment_method"))

    # 1. INSERT transaksi_penjualan
    transaksi = TransaksiPenjualan(
        transaksi_sample_id=tx_id,
        koperasi_ref=koperasi_ref,
        nama_pelanggan=payload.get("customer_name", "Umum"),
        tanggal_dibuat=now,
        total_pembayaran=payload.get("calculated_total", 0),
        status_transaksi="Unpaid" if payment == "Hutang" else "Paid",
        metode_pembayaran=payment,
    )
    db.add(transaksi)

    # 2. INSERT barang_keluar_produk + UPDATE inventaris
    for item in payload.get("resolved_items", []):
        unit = normalize_unit(item.get("unit")) if item.get("unit") else None
        bk = BarangKeluarProduk(
            transaksi_sample_id=tx_id,
            produk_sample_id=item["produk_sample_id"],
            koperasi_ref=koperasi_ref,
            jumlah_keluar=item["quantity"],
            harga=item["unit_price"],
            total_nilai=item["subtotal"],
            nama_produk=item["nama_produk"],
            nama_tampilan=f"{item['nama_produk']} ({unit})" if unit else item["nama_produk"],
            status_transaksi=transaksi.status_transaksi,
            tanggal_keluar=now,
        )
        db.add(bk)

        # Decrement inventory
        inv_result = await db.execute(
            select(InventarisProduk).where(
                InventarisProduk.koperasi_ref == koperasi_ref,
                InventarisProduk.produk_sample_id == item["produk_sample_id"],
            )
        )
        inv = inv_result.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Inventory record not found for {item['produk_sample_id']}")
        current_stock = float(inv.stok or 0)
        if current_stock < item["quantity"]:
            raise ValueError(f"Insufficient stock: {item['nama_produk']} have {current_stock}, need {item['quantity']}")
        inv.stok = current_stock - item["quantity"]

    # 3. INSERT relasi_transaksi_pihak
    if payload.get("customer_ref"):
        relasi = RelasiTransaksiPihak(
            transaksi_sample_id=tx_id,
            anggota_ref=payload["customer_ref"],
            relationship_type="MEMBER_CUSTOMER",
            match_method="ai_parsed",
        )
        db.add(relasi)

    # 4. INSERT konfirmasi_pengguna
    konfirmasi = KonfirmasiPengguna(
        pesan_id=pesan.pesan_id,
        parsing_id=parsing.parsing_id,
        pengguna_id=user.pengguna_id,
        keputusan="YA",
    )
    db.add(konfirmasi)

    # 5. Update statuses
    parsing.status = "VALID"
    pesan.status = "CONFIRMED"
    pesan.processed_at = datetime.utcnow()
    await db.commit()
