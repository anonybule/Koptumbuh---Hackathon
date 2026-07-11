from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/mobile", tags=["mobile-knowledge"])


@router.get("/knowledge/search", response_model=ApiResponse)
async def search_knowledge(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ILIKE search on artikel_pengetahuan (judul + isi)."""
    offset, limit = offset_limit(page, per_page)
    params = {
        "r": user["koperasi_ref"],
        "q": f"%{q}%",
        "off": offset,
        "lim": limit,
    }
    where = (
        "(koperasi_ref IS NULL OR koperasi_ref=:r) "
        "AND COALESCE(status_aktif, TRUE) = TRUE "
        "AND (judul ILIKE :q OR isi ILIKE :q)"
    )
    try:
        total = (
            await db.execute(
                text(f"SELECT COUNT(*) FROM koptumbuh.artikel_pengetahuan WHERE {where}"),
                params,
            )
        ).scalar() or 0
        result = await db.execute(
            text(
                f"SELECT artikel_id, judul, kategori, sumber, "
                f"LEFT(isi, 300) AS preview, tags "
                f"FROM koptumbuh.artikel_pengetahuan WHERE {where} "
                f"ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST "
                f"OFFSET :off LIMIT :lim"
            ),
            params,
        )
        return ApiResponse(
            data=[
                {
                    "id": str(r[0]),
                    "judul": r[1],
                    "kategori": r[2],
                    "sumber": r[3],
                    "preview": r[4],
                    "tags": r[5],
                }
                for r in result.fetchall()
            ],
            meta=paginate(page, per_page, total),
        )
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Knowledge base unavailable")
