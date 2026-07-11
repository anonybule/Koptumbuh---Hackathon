"""TC-003: Full E2E YA commit → transaksi + barang_keluar + inventaris."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.services.state_machine import commit_transaction


@pytest.mark.asyncio
async def test_tc003_ya_commit_updates_stock():
    from app.database import AsyncSessionLocal
    from app.models.koptumbuh import ParsingPesan, PesanMasuk, PenggunaKoptumbuh
    from sqlalchemy import select

    koperasi_ref = "KOP-JasaAI-A1B2C3D4E5F6"

    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(
                select(PenggunaKoptumbuh).where(
                    PenggunaKoptumbuh.nomor_whatsapp == "628123456003"
                )
            )
        ).scalar_one_or_none()
        if not user:
            pytest.skip("Demo user missing")

        prod = (
            await db.execute(
                text(
                    """
                    SELECT p.produk_sample_id, p.nama_produk, i.stok,
                           (SELECT harga_jual FROM koptumbuh.barang_masuk_produk bm
                            WHERE bm.produk_sample_id = p.produk_sample_id
                            ORDER BY bm.tanggal_masuk DESC LIMIT 1) AS harga
                    FROM koptumbuh.produk_koperasi p
                    JOIN koptumbuh.inventaris_produk i
                      ON i.produk_sample_id = p.produk_sample_id AND i.koperasi_ref = p.koperasi_ref
                    WHERE p.koperasi_ref = :r AND i.stok >= 2
                    LIMIT 1
                    """
                ),
                {"r": koperasi_ref},
            )
        ).fetchone()
        if not prod or not prod[3]:
            pytest.skip("No product with stock+price for E2E")

        produk_id, nama, stok_before, harga = prod[0], prod[1], float(prod[2]), float(prod[3])
        qty = 1.0

        pesan = PesanMasuk(
            koperasi_ref=koperasi_ref,
            pengguna_id=user.pengguna_id,
            whatsapp_message_id=f"TC003-{uuid.uuid4().hex[:10]}",
            input_type="TEXT",
            raw_text=f"beli {qty} {nama}",
            status="PARSED",
        )
        db.add(pesan)
        await db.flush()

        payload = {
            "intent": "RECORD_SALE",
            "customer_name": "Bu Sari",
            "payment_method": "Cash",
            "resolved_items": [
                {
                    "produk_sample_id": produk_id,
                    "nama_produk": nama,
                    "quantity": qty,
                    "unit_price": harga,
                    "subtotal": round(qty * harga, 2),
                    "unit": "KG",
                }
            ],
            "calculated_total": round(qty * harga, 2),
        }
        parsing = ParsingPesan(
            pesan_id=pesan.pesan_id,
            detected_intent="RECORD_SALE",
            extracted_payload=payload,
            status="VALID",
            confidence_score=0.95,
        )
        db.add(parsing)
        await db.commit()
        await db.refresh(parsing)
        await db.refresh(pesan)

        await commit_transaction(parsing, pesan, user, db)

        stok_after = (
            await db.execute(
                text(
                    "SELECT stok FROM koptumbuh.inventaris_produk WHERE produk_sample_id=:p AND koperasi_ref=:r"
                ),
                {"p": produk_id, "r": koperasi_ref},
            )
        ).scalar()
        keluar = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.barang_keluar_produk WHERE produk_sample_id=:p AND koperasi_ref=:r AND tanggal_keluar::date = CURRENT_DATE"
                ),
                {"p": produk_id, "r": koperasi_ref},
            )
        ).scalar()
        tx = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r AND DATE(tanggal_dibuat)=CURRENT_DATE"
                ),
                {"r": koperasi_ref},
            )
        ).scalar()

    assert float(stok_after) == pytest.approx(stok_before - qty, abs=0.001)
    assert int(keluar) >= 1
    assert int(tx) >= 1
