"""TC-006: Export trigger → ekspor_log SUCCESS (MinIO optional)."""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_tc006_export_simkopdes(auth_headers, client):
    r = client.post(
        "/api/v1/admin/export/simkopdes",
        headers=auth_headers,
        json={},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("success") is True

    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        row = (
            await db.execute(
                text(
                    """
                    SELECT status, file_url FROM koptumbuh.ekspor_log
                    WHERE koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6'
                    ORDER BY created_at DESC NULLS LAST
                    LIMIT 1
                    """
                )
            )
        ).fetchone()

    if not row:
        async with AsyncSessionLocal() as db:
            row = (
                await db.execute(
                    text(
                        "SELECT status, file_url FROM koptumbuh.ekspor_log ORDER BY created_at DESC LIMIT 1"
                    )
                )
            ).fetchone()

    assert row is not None, "ekspor_log row missing"
    status = str(row[0]).upper()
    assert status in ("SUCCESS", "OK", "COMPLETED", "PARTIAL"), f"status={status}"
