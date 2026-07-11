"""Shared fixtures for KopTumbuh integration tests (TC-001–006)."""
from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient

# Ensure test-friendly defaults before app import
os.environ.setdefault("JWT_SECRET_KEY", "hackathon-jasaai-2026")
os.environ.setdefault("EVOLUTION_API_KEY", "")  # skip apikey check in tests unless set


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"phone": "628123456003", "password": "kop123"},
    )
    if resp.status_code != 200 or not resp.json().get("success"):
        pytest.skip(f"Login unavailable (is DB up?): {resp.text}")
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def msg_id() -> str:
    return f"TC-{uuid.uuid4().hex[:12]}"


def wa_payload(message_id: str, text: str, phone: str = "628123456003") -> dict:
    return {
        "event": "messages.upsert",
        "data": {
            "key": {"id": message_id, "remoteJid": f"{phone}@s.whatsapp.net"},
            "message": {"conversation": text, "messageType": "conversation"},
        },
    }
