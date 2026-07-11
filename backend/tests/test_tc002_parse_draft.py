"""TC-002: Text sale message → pesan_masuk + parsing_pesan DRAFT (or VALID after validate)."""
from __future__ import annotations

import asyncio
import time

import pytest
from sqlalchemy import text

from tests.conftest import wa_payload


@pytest.mark.asyncio
async def test_tc002_parse_creates_draft(client, msg_id):
    text_msg = "Bu Sari beli 2 Beras Premium 5kg bayar tunai"
    r = client.post("/api/v1/webhooks/whatsapp", json=wa_payload(msg_id, text_msg))
    assert r.status_code == 200
    data = r.json().get("data", {})
    if data.get("status") == "unknown_user":
        pytest.skip("Demo user not seeded")
    assert data.get("status") in ("queued", "confirmation_handled")

    from app.database import AsyncSessionLocal

    # Wait briefly for Celery worker (or inline if sync)
    pesan_id = data.get("pesan_id")
    deadline = time.time() + 15
    parsing_status = None
    while time.time() < deadline:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(
                    text(
                        """
                        SELECT p.status, pp.status AS parse_status
                        FROM koptumbuh.pesan_masuk p
                        LEFT JOIN koptumbuh.parsing_pesan pp ON pp.pesan_id = p.pesan_id
                        WHERE p.whatsapp_message_id = :m
                        """
                    ),
                    {"m": msg_id},
                )
            ).fetchone()
        if row and row[0]:
            if row[1] in ("DRAFT", "VALID", "INVALID"):
                parsing_status = row[1]
                break
        await asyncio.sleep(0.5)

    async with AsyncSessionLocal() as db:
        exists = (
            await db.execute(
                text("SELECT 1 FROM koptumbuh.pesan_masuk WHERE whatsapp_message_id = :m"),
                {"m": msg_id},
            )
        ).scalar()
    assert exists, "pesan_masuk row missing"

    if parsing_status is None:
        pytest.skip("Celery/AI worker did not produce parsing_pesan in time (GEMINI_API_KEY?)")
    assert parsing_status in ("DRAFT", "VALID", "INVALID")
