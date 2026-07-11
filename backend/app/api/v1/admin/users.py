import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-users"])

ALLOWED_ROLES = {"OPERATOR", "KETUA", "BENDAHARA", "PEMBINA", "ADMIN", "ANGGOTA"}


@router.get("/users", response_model=ApiResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    params: dict = {"off": offset, "lim": limit}
    where = "1=1"
    if user["role"] != "PEMBINA":
        where = "koperasi_ref=:r"
        params["r"] = user["koperasi_ref"]

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.pengguna_koptumbuh WHERE {where}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT pengguna_id, nama, nomor_whatsapp, role, status_aktif, koperasi_ref, created_at "
            f"FROM koptumbuh.pengguna_koptumbuh WHERE {where} "
            f"ORDER BY created_at DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "nama": r[1],
                "nomor_whatsapp": r[2],
                "role": r[3],
                "status_aktif": r[4],
                "koperasi_ref": r[5],
                "created_at": str(r[6]) if r[6] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/users", response_model=ApiResponse)
async def create_user(body: dict, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    nama = body.get("nama")
    wa = body.get("nomor_whatsapp")
    role = body.get("role", "OPERATOR")
    if not nama or not wa:
        raise HTTPException(status_code=422, detail="nama and nomor_whatsapp are required")
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Allowed: {sorted(ALLOWED_ROLES)}")

    koperasi_ref = body.get("koperasi_ref") or user["koperasi_ref"]
    if user["role"] != "PEMBINA":
        koperasi_ref = user["koperasi_ref"]

    pengurus = body.get("pengurus_ref")
    karyawan = body.get("karyawan_ref")
    if role not in ("PEMBINA", "ADMIN") and not pengurus and not karyawan:
        raise HTTPException(
            status_code=422,
            detail="pengurus_ref or karyawan_ref required for non-PEMBINA/ADMIN roles",
        )

    uid = str(uuid.uuid4())
    await db.execute(
        text(
            "INSERT INTO koptumbuh.pengguna_koptumbuh "
            "(pengguna_id, koperasi_ref, nama, nomor_whatsapp, role, status_aktif, pengurus_ref, karyawan_ref) "
            "VALUES (:id, :r, :n, :wa, :role, true, :pengurus, :karyawan)"
        ),
        {
            "id": uid,
            "r": koperasi_ref,
            "n": nama,
            "wa": wa,
            "role": role,
            "pengurus": pengurus,
            "karyawan": karyawan,
        },
    )
    await db.commit()
    return ApiResponse(data={"id": uid, "nama": nama, "role": role})


@router.patch("/users/{id}", response_model=ApiResponse)
async def update_user(
    id: str,
    body: dict,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    params: dict = {"id": id}
    scope = ""
    if user["role"] != "PEMBINA":
        scope = " AND koperasi_ref=:r"
        params["r"] = user["koperasi_ref"]

    exists = await db.execute(
        text(f"SELECT 1 FROM koptumbuh.pengguna_koptumbuh WHERE pengguna_id=:id{scope}"),
        params,
    )
    if not exists.scalar():
        raise HTTPException(status_code=404, detail="User not found")

    fields = []
    update_params: dict = {"id": id}
    if "role" in body:
        if body["role"] not in ALLOWED_ROLES:
            raise HTTPException(status_code=422, detail="Invalid role")
        fields.append("role=:role")
        update_params["role"] = body["role"]
    if "status_aktif" in body:
        fields.append("status_aktif=:aktif")
        update_params["aktif"] = body["status_aktif"]
    if "nama" in body:
        fields.append("nama=:nama")
        update_params["nama"] = body["nama"]
    if "nomor_whatsapp" in body:
        fields.append("nomor_whatsapp=:wa")
        update_params["wa"] = body["nomor_whatsapp"]
    if not fields:
        raise HTTPException(status_code=422, detail="No updatable fields provided")
    fields.append("updated_at=NOW()")
    await db.execute(
        text(f"UPDATE koptumbuh.pengguna_koptumbuh SET {', '.join(fields)} WHERE pengguna_id=:id"),
        update_params,
    )
    await db.commit()
    return ApiResponse(data={"id": id, "updated": True})
