"""TC-001: Duplicate whatsapp_message_id → second call returns duplicate, one DB row."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest import wa_payload


@pytest.mark.asyncio
async def test_tc001_duplicate_webhook(client, msg_id):
    payload = wa_payload(msg_id, "ping idempotency")

    r1 = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1.get("success") is True
    status1 = body1.get("data", {}).get("status")
    assert status1 in ("queued", "confirmation_handled", "unknown_user", "rate_limited")

    if status1 == "unknown_user":
        pytest.skip("Demo user not seeded")

    r2 = client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2.get("data", {}).get("status") == "duplicate"

    # Exactly one pesan_masuk row for this message id
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        count = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.pesan_masuk WHERE whatsapp_message_id = :m"
                ),
                {"m": msg_id},
            )
        ).scalar()
    assert int(count) == 1
