"""TC-004: UBAH reply → parsing SUPERSEDED, Redis cleared, no new transaction."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select, text

from app.services.state_machine import handle_confirmation_reply


@pytest.mark.asyncio
async def test_tc004_ubah_supersedes_draft():
    from app.database import AsyncSessionLocal
    from app.models.koptumbuh import ParsingPesan, PesanMasuk, PenggunaKoptumbuh
    from app.services.state_machine import redis_client

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

        tx_before = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r"
                ),
                {"r": koperasi_ref},
            )
        ).scalar()

        pesan_sale = PesanMasuk(
            koperasi_ref=koperasi_ref,
            pengguna_id=user.pengguna_id,
            whatsapp_message_id=f"TC004a-{uuid.uuid4().hex[:10]}",
            input_type="TEXT",
            raw_text="beli 1 Beras",
            status="PARSED",
        )
        db.add(pesan_sale)
        await db.flush()

        parsing = ParsingPesan(
            pesan_id=pesan_sale.pesan_id,
            detected_intent="RECORD_SALE",
            extracted_payload={"resolved_items": [], "calculated_total": 0},
            status="VALID",
            confidence_score=0.9,
        )
        db.add(parsing)
        await db.commit()
        await db.refresh(parsing)

        redis_client.set(
            f"session:{user.nomor_whatsapp}",
            json.dumps({"parsing_id": str(parsing.parsing_id), "intent": "RECORD_SALE"}),
            ex=900,
        )

        pesan_ubah = PesanMasuk(
            koperasi_ref=koperasi_ref,
            pengguna_id=user.pengguna_id,
            whatsapp_message_id=f"TC004b-{uuid.uuid4().hex[:10]}",
            input_type="TEXT",
            raw_text="UBAH",
            status="RECEIVED",
        )
        db.add(pesan_ubah)
        await db.commit()
        await db.refresh(pesan_ubah)

        handled = await handle_confirmation_reply(pesan_ubah, db)
        assert handled is True

        await db.refresh(parsing)
        assert parsing.status == "SUPERSEDED"
        assert redis_client.get(f"session:{user.nomor_whatsapp}") is None

        tx_after = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r"
                ),
                {"r": koperasi_ref},
            )
        ).scalar()
        assert int(tx_after) == int(tx_before)
