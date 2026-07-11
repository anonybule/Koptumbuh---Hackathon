from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-recommendations"])


@router.get("/recommendations", response_model=ApiResponse)
async def list_recommendations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = None,
    jenis: str | None = None,
    priority: str | None = None,
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
    else:
        where.append("status IN ('NEW','READ')")
    if jenis:
        where.append("jenis=:jenis")
        params["jenis"] = jenis
    if priority:
        where.append("priority=:pr")
        params["pr"] = priority
    clause = " AND ".join(where)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.rekomendasi WHERE {clause}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT rekomendasi_id, jenis, judul, isi_rekomendasi, priority, status, generated_at, "
            f"produk_sample_id, alasan "
            f"FROM koptumbuh.rekomendasi WHERE {clause} "
            f"ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, "
            f"generated_at DESC OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "jenis": r[1],
                "judul": r[2],
                "isi": r[3],
                "priority": r[4],
                "status": r[5],
                "generated_at": str(r[6]) if r[6] else None,
                "produk_sample_id": r[7],
                "alasan": r[8],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/recommendations/generate", response_model=ApiResponse)
async def generate_recommendations(user: dict = Depends(require_operator)):
    """Queue stockout recommendation generation for the current cooperative."""
    from app.workers.recommendations import generate_all_recommendations

    generate_all_recommendations.delay(user["koperasi_ref"])
    return ApiResponse(data={"status": "queued"})
