from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])

VALID_STATUSES = {"READ", "ACCEPTED", "REJECTED"}


class UpdateRecStatusBody(BaseModel):
    status: str


@router.get("/recommendations", response_model=ApiResponse)
async def list_recommendations(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = "koperasi_ref = :ref"
    params: dict = {"ref": ref, "offset": offset, "limit": limit}
    if status:
        where += " AND status = :status"
        params["status"] = status

    total = (await db.execute(
        text(f"SELECT COUNT(*) FROM koptumbuh.rekomendasi WHERE {where}"),
        {k: v for k, v in params.items() if k not in ("offset", "limit")},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            f"""SELECT rekomendasi_id, jenis, judul, isi_rekomendasi, alasan,
                       produk_sample_id, priority, status, generated_at
                FROM koptumbuh.rekomendasi
                WHERE {where}
                ORDER BY CASE priority
                    WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                    generated_at DESC
                OFFSET :offset LIMIT :limit"""
        ),
        params,
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "jenis": r[1],
                "judul": r[2],
                "isi": r[3],
                "alasan": r[4],
                "produk_sample_id": r[5],
                "priority": r[6],
                "status": r[7],
                "generated_at": str(r[8]) if r[8] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.patch("/recommendations/{rec_id}/status", response_model=ApiResponse)
async def update_recommendation_status(
    rec_id: UUID,
    body: UpdateRecStatusBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    status = body.status.upper()
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")

    result = await db.execute(
        text(
            "UPDATE koptumbuh.rekomendasi "
            "SET status=:status, actioned_at=NOW() "
            "WHERE rekomendasi_id=:id AND koperasi_ref=:ref "
            "RETURNING rekomendasi_id, status"
        ),
        {"status": status, "id": rec_id, "ref": user["koperasi_ref"]},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    return ApiResponse(data={"id": str(row[0]), "status": row[1]})
