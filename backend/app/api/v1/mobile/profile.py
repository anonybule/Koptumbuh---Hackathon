from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


class UpdateProfileBody(BaseModel):
    nama: str | None = None
    nomor_whatsapp: str | None = None


@router.get("/profile", response_model=ApiResponse)
async def get_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    kop = (await db.execute(
        text(
            "SELECT p.nama_koperasi, p.alamat_lengkap, p.status_registrasi, "
            "p.bentuk_koperasi, r.kode_wilayah "
            "FROM koptumbuh.profil_koperasi p "
            "JOIN koptumbuh.referensi_koperasi_wilayah r ON r.koperasi_ref = p.koperasi_ref "
            "WHERE p.koperasi_ref=:ref"
        ),
        {"ref": ref},
    )).fetchone()

    return ApiResponse(data={
        "pengguna_id": user["pengguna_id"],
        "nama": user["nama"],
        "nomor_whatsapp": user["nomor_whatsapp"],
        "role": user["role"],
        "koperasi_ref": ref,
        "koperasi": None if not kop else {
            "nama": kop[0],
            "alamat": kop[1],
            "status": kop[2],
            "bentuk": kop[3],
            "kode_wilayah": kop[4],
        },
    })


@router.patch("/profile", response_model=ApiResponse)
async def update_profile(
    body: UpdateProfileBody,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.nama is None and body.nomor_whatsapp is None:
        raise HTTPException(status_code=400, detail="Nothing to update")

    sets = ["updated_at = NOW()"]
    params: dict = {"id": user["pengguna_id"]}
    if body.nama is not None:
        sets.append("nama = :nama")
        params["nama"] = body.nama
    if body.nomor_whatsapp is not None:
        sets.append("nomor_whatsapp = :wa")
        params["wa"] = body.nomor_whatsapp

    row = (await db.execute(
        text(
            f"UPDATE koptumbuh.pengguna_koptumbuh SET {', '.join(sets)} "
            "WHERE pengguna_id=:id "
            "RETURNING pengguna_id, nama, nomor_whatsapp, role"
        ),
        params,
    )).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    await db.commit()
    return ApiResponse(data={
        "pengguna_id": str(row[0]),
        "nama": row[1],
        "nomor_whatsapp": row[2],
        "role": row[3],
    })
