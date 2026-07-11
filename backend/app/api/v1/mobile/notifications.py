from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


@router.get("/notifications", response_model=ApiResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    uid = user["pengguna_id"]
    offset, limit = offset_limit(page, per_page)

    total = (await db.execute(
        text(
            "SELECT COUNT(*) FROM koptumbuh.notifikasi_log "
            "WHERE koperasi_ref=:ref AND (pengguna_id=:uid OR pengguna_id IS NULL)"
        ),
        {"ref": ref, "uid": uid},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT notifikasi_id, channel, message_type, title, content, "
            "status, sent_at, read_at, created_at, rekomendasi_id "
            "FROM koptumbuh.notifikasi_log "
            "WHERE koperasi_ref=:ref AND (pengguna_id=:uid OR pengguna_id IS NULL) "
            "ORDER BY created_at DESC OFFSET :offset LIMIT :limit"
        ),
        {"ref": ref, "uid": uid, "offset": offset, "limit": limit},
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "channel": r[1],
                "message_type": r[2],
                "title": r[3],
                "content": r[4],
                "status": r[5],
                "sent_at": str(r[6]) if r[6] else None,
                "read_at": str(r[7]) if r[7] else None,
                "created_at": str(r[8]) if r[8] else None,
                "rekomendasi_id": str(r[9]) if r[9] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )
