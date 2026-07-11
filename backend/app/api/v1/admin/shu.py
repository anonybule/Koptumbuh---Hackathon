"""Admin SHU APIs — real-time estimation and member allocation."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse
from app.services.shu_service import compute_shu_summary, compute_shu_monthly, compute_member_shu

router = APIRouter(prefix="/admin/shu", tags=["admin-shu"])


@router.get("/summary", response_model=ApiResponse)
async def shu_summary(
    year: int | None = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await compute_shu_summary(db, user["koperasi_ref"], year or date.today().year)
    return ApiResponse(data=data)


@router.get("/monthly", response_model=ApiResponse)
async def shu_monthly(
    year: int | None = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await compute_shu_monthly(db, user["koperasi_ref"], year or date.today().year)
    return ApiResponse(data=rows)


@router.get("/members", response_model=ApiResponse)
async def shu_members(
    year: int | None = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    y = year or date.today().year
    summary = await compute_shu_summary(db, user["koperasi_ref"], y)
    members = await compute_member_shu(db, user["koperasi_ref"], y, summary)
    return ApiResponse(
        data={
            "tahun": y,
            "shu_bersih": summary["shu_bersih"],
            "pools": summary["pools"],
            "members": members,
            "member_count": len(members),
            "total_allocated": round(sum(m["estimasi_shu"] for m in members), 2),
        }
    )
