from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-village"])


@router.get("/village/commodities", response_model=ApiResponse)
async def village_commodities(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    kode_wilayah: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    where = ["1=1"]
    params: dict = {"off": offset, "lim": limit}
    if kode_wilayah:
        where.append("k.kode_wilayah=:kw")
        params["kw"] = kode_wilayah
    else:
        # Scope to cooperative's wilayah when possible
        where.append(
            "k.kode_wilayah IN ("
            "SELECT h.kode_wilayah FROM koptumbuh.referensi_koperasi_wilayah h WHERE h.koperasi_ref=:r"
            ")"
        )
        params["r"] = user["koperasi_ref"]
    clause = " AND ".join(where)

    total = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM koptumbuh.referensi_komoditas_desa k WHERE {clause}"),
            params,
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT k.komoditas_ref, k.kode_wilayah, k.nama_komoditas, k.luas_area, k.volume, "
            f"k.jumlah_sdm_terlibat, k.nilai_potensi_desa "
            f"FROM koptumbuh.referensi_komoditas_desa k WHERE {clause} "
            f"ORDER BY k.nama_komoditas OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "komoditas_ref": r[0],
                "kode_wilayah": r[1],
                "nama_komoditas": r[2],
                "luas_area": r[3],
                "volume": r[4],
                "jumlah_sdm": float(r[5]) if r[5] is not None else None,
                "nilai_potensi": int(r[6]) if r[6] is not None else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/village/profiles", response_model=ApiResponse)
async def village_profiles(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    params = {"r": user["koperasi_ref"], "off": offset, "lim": limit}
    total = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM koptumbuh.referensi_profil_desa p "
                "WHERE p.kode_wilayah IN ("
                "SELECT h.kode_wilayah FROM koptumbuh.referensi_koperasi_wilayah h WHERE h.koperasi_ref=:r"
                ")"
            ),
            params,
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            "SELECT p.kode_wilayah, p.tahun_populasi, p.total_penduduk, p.penduduk_laki_laki, "
            "p.penduduk_perempuan, p.tahun_pendanaan, p.anggaran_dana_desa, "
            "w.desa_kelurahan, w.kecamatan, w.kab_kota, w.provinsi "
            "FROM koptumbuh.referensi_profil_desa p "
            "LEFT JOIN koptumbuh.referensi_wilayah w ON w.kode_wilayah=p.kode_wilayah "
            "WHERE p.kode_wilayah IN ("
            "SELECT h.kode_wilayah FROM koptumbuh.referensi_koperasi_wilayah h WHERE h.koperasi_ref=:r"
            ") ORDER BY p.kode_wilayah OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "kode_wilayah": r[0],
                "tahun_populasi": r[1],
                "total_penduduk": r[2],
                "penduduk_laki_laki": r[3],
                "penduduk_perempuan": r[4],
                "tahun_pendanaan": r[5],
                "anggaran_dana_desa": float(r[6] or 0) if r[6] is not None else None,
                "desa_kelurahan": r[7],
                "kecamatan": r[8],
                "kab_kota": r[9],
                "provinsi": r[10],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )
