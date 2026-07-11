from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/messages", response_model=ApiResponse)
async def list_messages(
    status: str | None = Query(None),
    since: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "m.koperasi_ref = :ref"
    params: dict = {"ref": ref, "offset": offset, "limit": limit}
    if status:
        where += " AND m.status = :status"
        params["status"] = status
    if since:
        where += " AND m.received_at > :since"
        params["since"] = since

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM koptumbuh.pesan_masuk m WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("offset", "limit")},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            f"""SELECT m.pesan_id, m.input_type, m.raw_text, m.status,
                       m.received_at, m.pengguna_id
                FROM koptumbuh.pesan_masuk m
                WHERE {where}
                ORDER BY m.received_at DESC
                OFFSET :offset LIMIT :limit"""
        ),
        params,
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "input_type": r[1],
                "raw_text": r[2],
                "status": r[3],
                "received_at": str(r[4]) if r[4] else None,
                "pengguna_id": str(r[5]) if r[5] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/messages/{pesan_id}", response_model=ApiResponse)
async def get_message(
    pesan_id: UUID,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    msg = (await db.execute(
        text(
            "SELECT pesan_id, input_type, raw_text, media_url, status, "
            "received_at, processed_at, pengguna_id "
            "FROM koptumbuh.pesan_masuk "
            "WHERE pesan_id=:id AND koperasi_ref=:ref"
        ),
        {"id": pesan_id, "ref": ref},
    )).fetchone()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    parsing = (await db.execute(
        text(
            "SELECT parsing_id, detected_intent, transcription_text, extracted_payload, "
            "confidence_score, validation_errors, status, created_at "
            "FROM koptumbuh.parsing_pesan "
            "WHERE pesan_id=:id ORDER BY created_at DESC LIMIT 1"
        ),
        {"id": pesan_id},
    )).fetchone()

    return ApiResponse(data={
        "id": str(msg[0]),
        "input_type": msg[1],
        "raw_text": msg[2],
        "media_url": msg[3],
        "status": msg[4],
        "received_at": str(msg[5]) if msg[5] else None,
        "processed_at": str(msg[6]) if msg[6] else None,
        "pengguna_id": str(msg[7]) if msg[7] else None,
        "parsing": None if not parsing else {
            "id": str(parsing[0]),
            "intent": parsing[1],
            "transcription": parsing[2],
            "payload": parsing[3],
            "confidence": float(parsing[4]) if parsing[4] is not None else None,
            "validation_errors": parsing[5],
            "status": parsing[6],
            "created_at": str(parsing[7]) if parsing[7] else None,
        },
    })
