"""ChatHub — WhatsApp inbox proxy via Evolution API, with DB fallback."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse
from app.services.whatsapp_service import whatsapp_service

router = APIRouter(prefix="/admin/chathub", tags=["admin-chathub"])


def _normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    digits = "".join(c for c in value if c.isdigit())
    if digits.startswith("0") and len(digits) >= 10:
        digits = "62" + digits[1:]
    return digits


def _jid_to_phone(jid: str | None) -> str:
    if not jid:
        return ""
    local = jid.split("@")[0]
    return _normalize_phone(local.split(":")[0])


def _phone_to_jid(phone: str) -> str:
    p = _normalize_phone(phone)
    return f"{p}@s.whatsapp.net" if p else ""


def _extract_message_text(msg: dict) -> str:
    if not isinstance(msg, dict):
        return ""
    for key in ("message", "content", "body"):
        nested = msg.get(key)
        if isinstance(nested, str) and nested.strip():
            return nested
        if isinstance(nested, dict):
            for tk in (
                "conversation",
                "extendedTextMessage",
                "imageMessage",
                "documentMessage",
                "audioMessage",
            ):
                part = nested.get(tk)
                if isinstance(part, str) and part.strip():
                    return part
                if isinstance(part, dict):
                    caption = part.get("caption") or part.get("text") or ""
                    if caption:
                        return str(caption)
                    if tk == "imageMessage":
                        return "[gambar]"
                    if tk == "documentMessage":
                        return part.get("fileName") or "[dokumen]"
                    if tk == "audioMessage":
                        return "[audio]"
            if nested.get("conversation"):
                return str(nested["conversation"])
    return str(msg.get("text") or msg.get("raw_text") or "")


def _normalize_evolution_chat(raw: dict) -> dict:
    jid = (
        raw.get("remoteJid")
        or raw.get("id")
        or (raw.get("key") or {}).get("remoteJid")
        or ""
    )
    if isinstance(jid, dict):
        jid = jid.get("remoteJid") or ""
    name = (
        raw.get("pushName")
        or raw.get("name")
        or raw.get("notify")
        or raw.get("verifiedName")
        or _jid_to_phone(str(jid))
        or "Tanpa nama"
    )
    last = raw.get("lastMessage") or raw.get("last_message") or {}
    preview = ""
    if isinstance(last, dict):
        preview = _extract_message_text(last) or last.get("message") or ""
        if isinstance(preview, dict):
            preview = _extract_message_text({"message": preview})
    updated = (
        raw.get("updatedAt")
        or raw.get("updated_at")
        or raw.get("conversationTimestamp")
        or raw.get("lastMsgTimestamp")
    )
    return {
        "id": str(jid),
        "remote_jid": str(jid),
        "phone": _jid_to_phone(str(jid)),
        "name": str(name),
        "preview": str(preview)[:160] if preview else "",
        "updated_at": str(updated) if updated is not None else None,
        "source": "evolution",
        "unread": int(raw.get("unreadCount") or raw.get("unread") or 0),
    }


def _normalize_evolution_message(raw: dict) -> dict:
    key = raw.get("key") if isinstance(raw.get("key"), dict) else {}
    from_me = bool(key.get("fromMe") or raw.get("fromMe") or raw.get("from_me"))
    remote = key.get("remoteJid") or raw.get("remoteJid") or ""
    text_body = _extract_message_text(raw)
    ts = (
        raw.get("messageTimestamp")
        or raw.get("timestamp")
        or raw.get("received_at")
        or raw.get("created_at")
    )
    return {
        "id": key.get("id") or raw.get("id") or raw.get("whatsapp_message_id") or "",
        "remote_jid": str(remote),
        "from_me": from_me,
        "text": text_body,
        "timestamp": str(ts) if ts is not None else None,
        "source": "evolution",
    }


class SendMessageBody(BaseModel):
    number: str = Field(..., min_length=8, description="WhatsApp number, e.g. 62812...")
    text: str = Field(..., min_length=1, max_length=4000)


@router.get("/status", response_model=ApiResponse)
async def chathub_status(user: dict = Depends(get_current_user)):
    _ = user
    state = await whatsapp_service.connection_state()
    return ApiResponse(
        data={
            "instance": state.get("instance") or whatsapp_service.instance,
            "state": state.get("state", "unknown"),
            "connected": str(state.get("state", "")).lower() in ("open", "connected", "online"),
            "evolution_ok": bool(state.get("success")),
            "error": state.get("error"),
        }
    )


@router.get("/qr", response_model=ApiResponse)
async def chathub_qr(user: dict = Depends(get_current_user)):
    _ = user
    result = await whatsapp_service.connect_qr()
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error") or "Evolution QR unavailable")
    return ApiResponse(
        data={
            "instance": result.get("instance"),
            "qr": result.get("qr"),
            "pairing_code": result.get("pairing_code"),
        }
    )


@router.get("/chats", response_model=ApiResponse)
async def list_chats(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    evo = await whatsapp_service.find_chats()
    chats: list[dict] = []
    if evo.get("success"):
        for raw in evo.get("chats") or []:
            if isinstance(raw, dict):
                chats.append(_normalize_evolution_chat(raw))

    # DB contacts / recent inbound as fallback or merge
    rows = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (phone) phone, name, preview, updated_at FROM (
                  SELECT p.nomor_whatsapp AS phone, p.nama AS name,
                         '' AS preview, p.updated_at AS updated_at
                  FROM koptumbuh.pengguna_koptumbuh p
                  WHERE p.koperasi_ref=:r AND p.nomor_whatsapp IS NOT NULL AND p.nomor_whatsapp <> ''
                  UNION ALL
                  SELECT c.nomor_whatsapp, c.nama_pelanggan, '', c.updated_at
                  FROM koptumbuh.pelanggan_koptumbuh c
                  WHERE c.koperasi_ref=:r AND c.nomor_whatsapp IS NOT NULL AND c.nomor_whatsapp <> ''
                  UNION ALL
                  SELECT COALESCE(u.nomor_whatsapp, ''), COALESCE(u.nama, 'Pengguna'),
                         LEFT(COALESCE(m.raw_text,''), 120), m.received_at
                  FROM koptumbuh.pesan_masuk m
                  LEFT JOIN koptumbuh.pengguna_koptumbuh u ON u.pengguna_id=m.pengguna_id
                  WHERE m.koperasi_ref=:r
                ) x
                WHERE phone IS NOT NULL AND phone <> ''
                ORDER BY phone, updated_at DESC NULLS LAST
                """
            ),
            {"r": ref},
        )
    ).fetchall()

    by_phone = {_normalize_phone(c.get("phone")): c for c in chats if c.get("phone")}
    for r in rows:
        phone = _normalize_phone(r[0])
        if not phone:
            continue
        if phone in by_phone:
            existing = by_phone[phone]
            if not existing.get("name") or existing["name"] == phone:
                existing["name"] = r[1] or existing["name"]
            if not existing.get("preview") and r[2]:
                existing["preview"] = r[2]
            continue
        chat = {
            "id": _phone_to_jid(phone),
            "remote_jid": _phone_to_jid(phone),
            "phone": phone,
            "name": r[1] or phone,
            "preview": r[2] or "",
            "updated_at": r[3].isoformat() if r[3] else None,
            "source": "database",
            "unread": 0,
        }
        chats.append(chat)
        by_phone[phone] = chat

    chats.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    return ApiResponse(
        data={
            "chats": chats,
            "evolution_ok": bool(evo.get("success")),
            "evolution_error": evo.get("error"),
        }
    )


@router.get("/messages", response_model=ApiResponse)
async def list_messages(
    remote_jid: str | None = Query(None),
    phone: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    jid = remote_jid or _phone_to_jid(phone or "")
    phone_n = _normalize_phone(phone) or _jid_to_phone(jid)
    if not jid and not phone_n:
        raise HTTPException(status_code=400, detail="remote_jid or phone required")

    messages: list[dict] = []
    evo_ok = False
    evo_error = None
    if jid:
        evo = await whatsapp_service.find_messages(jid, limit=limit)
        evo_ok = bool(evo.get("success"))
        evo_error = evo.get("error")
        if evo_ok:
            for raw in evo.get("messages") or []:
                if isinstance(raw, dict):
                    messages.append(_normalize_evolution_message(raw))

    if not messages and phone_n:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT m.whatsapp_message_id, m.raw_text, m.received_at, m.input_type,
                           u.nomor_whatsapp, u.nama
                    FROM koptumbuh.pesan_masuk m
                    LEFT JOIN koptumbuh.pengguna_koptumbuh u ON u.pengguna_id=m.pengguna_id
                    WHERE m.koperasi_ref=:r
                      AND regexp_replace(COALESCE(u.nomor_whatsapp,''), '[^0-9]', '', 'g') LIKE :phone
                    ORDER BY m.received_at DESC NULLS LAST
                    LIMIT :lim
                    """
                ),
                {"r": ref, "phone": f"%{phone_n}%", "lim": limit},
            )
        ).fetchall()
        for r in rows:
            if _normalize_phone(r[4]) and _normalize_phone(r[4]) != phone_n:
                continue
            messages.append(
                {
                    "id": r[0] or "",
                    "remote_jid": jid or _phone_to_jid(phone_n),
                    "from_me": False,
                    "text": r[1] or f"[{r[3] or 'pesan'}]",
                    "timestamp": r[2].isoformat() if r[2] else None,
                    "source": "database",
                }
            )

    # Oldest → newest for chat UI
    messages.sort(key=lambda m: m.get("timestamp") or "")
    return ApiResponse(
        data={
            "remote_jid": jid or _phone_to_jid(phone_n),
            "phone": phone_n,
            "messages": messages[-limit:],
            "evolution_ok": evo_ok,
            "evolution_error": evo_error,
        }
    )


@router.post("/send", response_model=ApiResponse)
async def send_chat_message(
    body: SendMessageBody,
    user: dict = Depends(get_current_user),
):
    _ = user
    number = _normalize_phone(body.number)
    if len(number) < 10:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp number")
    result = await whatsapp_service.send_message(number, body.text.strip())
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error") or "Failed to send via Evolution")
    return ApiResponse(
        data={
            "message_id": result.get("message_id"),
            "number": number,
            "text": body.text.strip(),
        }
    )
