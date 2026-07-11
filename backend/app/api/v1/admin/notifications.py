from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-notifications"])


@router.get("/notifications", response_model=ApiResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str | None = None,
    channel: str | None = None,
    message_type: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if status:
        where.append("status=:st")
        params["st"] = status
    if channel:
        where.append("channel=:ch")
        params["ch"] = channel
    if message_type:
        where.append("message_type=:mt")
        params["mt"] = message_type
    clause = " AND ".join(where)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.notifikasi_log WHERE {clause}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT notifikasi_id, channel, message_type, title, content, status, "
            f"pengguna_id, rekomendasi_id, sent_at, read_at, created_at "
            f"FROM koptumbuh.notifikasi_log WHERE {clause} "
            f"ORDER BY created_at DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "channel": r[1],
                "message_type": r[2],
                "title": r[3],
                "content": r[4],
                "status": r[5],
                "pengguna_id": str(r[6]) if r[6] else None,
                "rekomendasi_id": str(r[7]) if r[7] else None,
                "sent_at": str(r[8]) if r[8] else None,
                "read_at": str(r[9]) if r[9] else None,
                "created_at": str(r[10]) if r[10] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )
