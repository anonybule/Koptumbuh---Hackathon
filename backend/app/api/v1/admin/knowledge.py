import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_admin, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-knowledge"])


@router.get("/knowledge", response_model=ApiResponse)
async def list_knowledge(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    kategori: str | None = None,
    q: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    where = ["(koperasi_ref IS NULL OR koperasi_ref=:r)"]
    params: dict = {"r": user["koperasi_ref"], "off": offset, "lim": limit}
    if kategori:
        where.append("kategori=:kat")
        params["kat"] = kategori
    if q:
        where.append("(judul ILIKE :q OR isi ILIKE :q)")
        params["q"] = f"%{q}%"
    clause = " AND ".join(where)

    total = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM koptumbuh.artikel_pengetahuan WHERE {clause}"),
            params,
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT artikel_id, judul, kategori, sumber, versi, tags, status_aktif, created_at, updated_at, "
            f"LEFT(isi, 200) AS preview "
            f"FROM koptumbuh.artikel_pengetahuan WHERE {clause} "
            f"ORDER BY created_at DESC NULLS LAST OFFSET :off LIMIT :lim"
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
                "versi": r[4],
                "tags": r[5],
                "status_aktif": r[6],
                "created_at": str(r[7]) if r[7] else None,
                "updated_at": str(r[8]) if r[8] else None,
                "preview": r[9],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/knowledge", response_model=ApiResponse)
async def create_knowledge(body: dict, user: dict = Depends(require_operator), db: AsyncSession = Depends(get_db)):
    judul = body.get("judul")
    isi = body.get("isi")
    if not judul or not isi:
        raise HTTPException(status_code=422, detail="judul and isi are required")
    aid = str(uuid.uuid4())
    tags = body.get("tags")
    # artikel_pengetahuan.tags is TEXT[]; accept list or leave null
    await db.execute(
        text(
            "INSERT INTO koptumbuh.artikel_pengetahuan "
            "(artikel_id, koperasi_ref, judul, kategori, isi, sumber, versi, tags, status_aktif) "
            "VALUES (:id, :r, :judul, :kat, :isi, :sumber, :versi, "
            "CASE WHEN :tags IS NULL THEN NULL ELSE string_to_array(:tags, ',') END, true)"
        ),
        {
            "id": aid,
            "r": user["koperasi_ref"],
            "judul": judul,
            "kat": body.get("kategori"),
            "isi": isi,
            "sumber": body.get("sumber"),
            "versi": body.get("versi"),
            "tags": ",".join(tags) if isinstance(tags, list) else tags,
        },
    )
    await db.commit()
    return ApiResponse(data={"id": aid, "judul": judul})


@router.patch("/knowledge/{id}", response_model=ApiResponse)
async def update_knowledge(
    id: str,
    body: dict,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    exists = await db.execute(
        text(
            "SELECT 1 FROM koptumbuh.artikel_pengetahuan "
            "WHERE artikel_id=:id AND (koperasi_ref IS NULL OR koperasi_ref=:r)"
        ),
        {"id": id, "r": user["koperasi_ref"]},
    )
    if not exists.scalar():
        raise HTTPException(status_code=404, detail="Article not found")

    fields = []
    params: dict = {"id": id}
    for col in ("judul", "kategori", "isi", "sumber", "versi", "status_aktif"):
        if col in body:
            fields.append(f"{col}=:{col}")
            params[col] = body[col]
    if "tags" in body:
        tags = body["tags"]
        fields.append("tags=CASE WHEN :tags IS NULL THEN NULL ELSE string_to_array(:tags, ',') END")
        params["tags"] = ",".join(tags) if isinstance(tags, list) else tags
    if not fields:
        raise HTTPException(status_code=422, detail="No updatable fields provided")
    fields.append("updated_at=NOW()")
    await db.execute(
        text(f"UPDATE koptumbuh.artikel_pengetahuan SET {', '.join(fields)} WHERE artikel_id=:id"),
        params,
    )
    await db.commit()
    return ApiResponse(data={"id": id, "updated": True})


@router.delete("/knowledge/{id}", response_model=ApiResponse)
async def delete_knowledge(id: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            "DELETE FROM koptumbuh.artikel_pengetahuan "
            "WHERE artikel_id=:id AND (koperasi_ref IS NULL OR koperasi_ref=:r) RETURNING artikel_id"
        ),
        {"id": id, "r": user["koperasi_ref"]},
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Article not found")
    await db.commit()
    return ApiResponse(data={"id": id, "deleted": True})
