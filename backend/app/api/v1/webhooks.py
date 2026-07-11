from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.config import settings
from app.models.koptumbuh import PenggunaKoptumbuh, PesanMasuk
from app.schemas.common import ApiResponse
import redis

router = APIRouter(prefix="/webhooks", tags=["webhook"])
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _expected_api_key() -> str:
    """Prefer Evolution key; fall back to WHATSAPP_API_KEY if set."""
    return (settings.EVOLUTION_API_KEY or settings.WHATSAPP_API_KEY or "").strip()


def _verify_evolution_apikey(request: Request) -> None:
    """Accept apikey / x-evolution-apikey when a key is configured; skip in dev if unset."""
    expected = _expected_api_key()
    if not expected:
        return  # dev mode — no key configured
    provided = (
        request.headers.get("apikey")
        or request.headers.get("x-evolution-apikey")
        or ""
    ).strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid Evolution API key")


def _nested_media_url(msg: dict) -> str | None:
    for key in ("documentMessage", "videoMessage", "stickerMessage"):
        nested = msg.get(key) or {}
        if nested.get("url"):
            return nested["url"]
    return None


def _extract_media_url(msg: dict, input_type: str) -> str | None:
    if input_type == "VOICE":
        audio = msg.get("audioMessage") or msg.get("audio") or {}
        return audio.get("url") or msg.get("mediaUrl") or _nested_media_url(msg)
    if input_type == "PHOTO":
        image = msg.get("imageMessage") or msg.get("image") or {}
        return image.get("url") or msg.get("mediaUrl") or _nested_media_url(msg)
    return msg.get("mediaUrl") or _nested_media_url(msg)


def _voice_duration_seconds(msg: dict, data: dict) -> float | None:
    audio = msg.get("audioMessage") or msg.get("audio") or {}
    for candidate in (
        audio.get("seconds"),
        audio.get("duration"),
        data.get("seconds"),
        data.get("messageTimestamp"),  # not duration — skip if huge
    ):
        if candidate is None:
            continue
        try:
            val = float(candidate)
            # messageTimestamp is unix epoch — ignore values that look like timestamps
            if val > 10_000:
                continue
            return val
        except (TypeError, ValueError):
            continue
    return None


def _photo_caption_and_confidence(msg: dict, data: dict) -> tuple[str | None, float | None]:
    image = msg.get("imageMessage") or msg.get("image") or {}
    caption = (
        image.get("caption")
        or msg.get("caption")
        or data.get("caption")
        or None
    )
    if isinstance(caption, str):
        caption = caption.strip() or None

    confidence = None
    for candidate in (
        image.get("confidence"),
        image.get("confidence_score"),
        msg.get("confidence"),
        msg.get("confidence_score"),
        data.get("confidence"),
        data.get("confidence_score"),
    ):
        if candidate is None:
            continue
        try:
            confidence = float(candidate)
            break
        except (TypeError, ValueError):
            continue
    return caption, confidence


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """WhatsApp webhook verification challenge (Evolution API)."""
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=params.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.post("/whatsapp", response_model=ApiResponse)
async def receive_whatsapp(request: Request, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Evolution API webhook receiver.
    1. Verify apikey header (when configured)
    2. Extract message_id, sender, type, content
    3. Rate limit + idempotency check
    4. Resolve sender → pengguna_id + koperasi_ref
    5. INSERT pesan_masuk (graceful duplicate on unique violation)
    6. Push to Celery queue (unless NEEDS_REVIEW skip-AI path)
    7. Return 200 OK
    """
    _verify_evolution_apikey(request)

    # Ignore non-message events
    if payload.get("event") != "messages.upsert":
        return ApiResponse(data={"status": "ignored"})

    data = payload.get("data", {})
    if not data or not isinstance(data, dict):
        return ApiResponse(data={"status": "invalid_payload"})

    message_id = data.get("key", {}).get("id", "")
    if not message_id:
        return ApiResponse(data={"status": "invalid_message_id"})

    sender_raw = data.get("key", {}).get("remoteJid", "")
    sender_phone = sender_raw.split("@")[0] if "@" in sender_raw else sender_raw
    if not sender_phone:
        return ApiResponse(data={"status": "invalid_sender"})

    msg = data.get("message", {})
    if not msg or not isinstance(msg, dict):
        return ApiResponse(data={"status": "invalid_message"})

    # Rate limit: 60 messages / minute per sender
    rate_key = f"rate:wa:{sender_phone}"
    try:
        count = redis_client.incr(rate_key)
        if count == 1:
            redis_client.expire(rate_key, 60)
        if count > 60:
            return ApiResponse(data={"status": "rate_limited"})
    except Exception:
        pass  # Redis down — continue without rate limit

    # Idempotency check
    lock_key = f"lock:wa:{message_id}"
    try:
        if not redis_client.set(lock_key, "processing", ex=30, nx=True):
            return ApiResponse(data={"status": "duplicate"})
    except Exception:
        pass  # Redis down — rely on DB unique constraint

    # Classify input (messageType may live on data or inside message)
    msg_type = (
        data.get("messageType")
        or msg.get("messageType")
        or ("conversation" if msg.get("conversation") else "")
        or ""
    )
    msg_type_l = str(msg_type).lower()

    skip_ai = False
    media_url = None
    content = None
    status = "RECEIVED"

    if msg_type_l in ("conversation", "extendedtextmessage") or "text" in msg_type_l or msg.get("conversation"):
        input_type = "TEXT"
        content = msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text") or (msg.get("text") or {}).get("text", "")
    elif "audio" in msg_type_l or msg.get("audioMessage"):
        input_type = "VOICE"
        media_url = _extract_media_url(msg, input_type)
        duration = _voice_duration_seconds(msg, data)
        max_secs = settings.MAX_AUDIO_SECONDS or 60
        if duration is not None and duration > max_secs:
            status = "NEEDS_REVIEW"
            skip_ai = True
            content = f"[VOICE too long: {duration:.0f}s > {max_secs}s]"
    elif "image" in msg_type_l or msg.get("imageMessage"):
        input_type = "PHOTO"
        media_url = _extract_media_url(msg, input_type)
        caption, confidence = _photo_caption_and_confidence(msg, data)
        content = caption
        # Caption is optional — Gemini OCR can read the image.
        # Only skip AI when an explicit low confidence score is provided upstream.
        min_conf = settings.MIN_PHOTO_CONFIDENCE
        low_confidence = confidence is not None and confidence < min_conf
        if low_confidence:
            status = "NEEDS_REVIEW"
            skip_ai = True
            content = content or f"[PHOTO low confidence: {confidence}]"
    else:
        input_type = "DOCUMENT"
        content = None
        media_url = _extract_media_url(msg, "DOCUMENT")

    # Resolve sender
    result = await db.execute(
        select(PenggunaKoptumbuh).where(
            PenggunaKoptumbuh.nomor_whatsapp == sender_phone,
            PenggunaKoptumbuh.status_aktif == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        return ApiResponse(data={"status": "unknown_user"})

    # Validate bounds (text length)
    if content and len(content) > settings.MAX_TEXT_LENGTH:
        content = content[:settings.MAX_TEXT_LENGTH]

    # Write pesan_masuk
    pesan = PesanMasuk(
        koperasi_ref=user.koperasi_ref,
        pengguna_id=user.pengguna_id,
        whatsapp_message_id=message_id,
        input_type=input_type,
        raw_text=content,
        media_url=media_url,
        status=status,
    )
    db.add(pesan)
    try:
        await db.commit()
        await db.refresh(pesan)
    except IntegrityError:
        await db.rollback()
        return ApiResponse(data={"status": "duplicate"})

    # Skip AI for voice-too-long / photo-needs-review
    if skip_ai:
        return ApiResponse(data={"status": "needs_review", "pesan_id": str(pesan.pesan_id)})

    # Check if this is a confirmation reply (YA/UBAH/BATAL)
    if content and content.strip().upper() in ("YA", "UBAH", "BATAL"):
        from app.services.state_machine import handle_confirmation_reply
        was_handled = await handle_confirmation_reply(pesan, db)
        if was_handled:
            return ApiResponse(data={"status": "confirmation_handled"})

    # Push to Celery pipeline
    from app.workers.router import process_message
    process_message.delay(str(pesan.pesan_id))

    return ApiResponse(data={"status": "queued", "pesan_id": str(pesan.pesan_id)})
