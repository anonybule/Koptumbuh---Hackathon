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

VALID_DELIVERY_STATUSES = {"MENUNGGU", "DIKIRIM", "TIBA", "GAGAL"}


class UpdateDeliveryStatusBody(BaseModel):
    status: str


@router.get("/deliveries", response_model=ApiResponse)
async def list_deliveries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    try:
        total = (await db.execute(
            text("SELECT COUNT(*) FROM koptumbuh.pengiriman WHERE koperasi_ref=:ref"),
            {"ref": ref},
        )).scalar() or 0

        rows = (await db.execute(
            text(
                "SELECT pengiriman_id, transaksi_sample_id, tipe_pengiriman, "
                "alamat_tujuan, kurir_id, status, dibuat_pada, diperbarui_pada "
                "FROM koptumbuh.pengiriman WHERE koperasi_ref=:ref "
                "ORDER BY dibuat_pada DESC OFFSET :offset LIMIT :limit"
            ),
            {"ref": ref, "offset": offset, "limit": limit},
        )).fetchall()

        return ApiResponse(
            data=[
                {
                    "id": str(r[0]),
                    "transaksi_sample_id": r[1],
                    "tipe": r[2],
                    "alamat": r[3],
                    "kurir_id": r[4],
                    "status": r[5],
                    "created_at": str(r[6]) if r[6] else None,
                    "updated_at": str(r[7]) if r[7] else None,
                }
                for r in rows
            ],
            meta=paginate(page, per_page, total),
        )
    except Exception:
        await db.rollback()
        return ApiResponse(data=[], meta=paginate(page, per_page, 0))


@router.patch("/deliveries/{delivery_id}/status", response_model=ApiResponse)
async def update_delivery_status(
    delivery_id: UUID,
    body: UpdateDeliveryStatusBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    status = body.status.upper()
    if status not in VALID_DELIVERY_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(VALID_DELIVERY_STATUSES)}",
        )

    try:
        row = (await db.execute(
            text(
                "UPDATE koptumbuh.pengiriman "
                "SET status=:status, diperbarui_pada=NOW() "
                "WHERE pengiriman_id=:id AND koperasi_ref=:ref "
                "RETURNING pengiriman_id, status"
            ),
            {"status": status, "id": delivery_id, "ref": user["koperasi_ref"]},
        )).fetchone()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Deliveries table not available")

    if not row:
        raise HTTPException(status_code=404, detail="Delivery not found")
    await db.commit()
    return ApiResponse(data={"id": str(row[0]), "status": row[1]})
