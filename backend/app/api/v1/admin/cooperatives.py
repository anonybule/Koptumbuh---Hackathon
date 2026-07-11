from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-cooperatives"])


def _can_access(user: dict, ref: str) -> bool:
    if user["role"] in ("PEMBINA", "ADMIN"):
        return True
    return user.get("koperasi_ref") == ref


@router.get("/cooperatives", response_model=ApiResponse)
async def list_cooperatives(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: str | None = None,
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    where = ["1=1"]
    params: dict = {"off": offset, "lim": limit}
    if user["role"] not in ("PEMBINA", "ADMIN"):
        where.append("p.koperasi_ref=:r")
        params["r"] = user["koperasi_ref"]
    if q:
        where.append("(p.nama_koperasi ILIKE :q OR p.koperasi_ref ILIKE :q OR p.nik_koperasi ILIKE :q)")
        params["q"] = f"%{q}%"
    clause = " AND ".join(where)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.profil_koperasi p WHERE {clause}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT p.koperasi_ref, p.nama_koperasi, p.status_registrasi, p.bentuk_koperasi, "
            f"p.kategori_usaha, p.nik_koperasi, p.alamat_lengkap, h.kode_wilayah "
            f"FROM koptumbuh.profil_koperasi p "
            f"LEFT JOIN koptumbuh.referensi_koperasi_wilayah h ON h.koperasi_ref=p.koperasi_ref "
            f"WHERE {clause} ORDER BY p.nama_koperasi OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "koperasi_ref": r[0],
                "nama_koperasi": r[1],
                "status_registrasi": r[2],
                "bentuk_koperasi": r[3],
                "kategori_usaha": r[4],
                "nik_koperasi": r[5],
                "alamat": r[6],
                "kode_wilayah": r[7],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/cooperatives/{ref}", response_model=ApiResponse)
async def cooperative_detail(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(
        text(
            "SELECT p.koperasi_ref, p.nama_koperasi, p.status_registrasi, p.bentuk_koperasi, p.kategori_usaha, "
            "p.nik_koperasi, p.alamat_lengkap, p.kode_pos, p.koordinat_dibulatkan, p.modal_awal, "
            "p.sumber_persetujuan, p.tentang_koperasi, p.pola_pengelolaan, p.metode_pengisian, "
            "h.kode_wilayah, w.provinsi, w.kab_kota, w.kecamatan, w.desa_kelurahan "
            "FROM koptumbuh.profil_koperasi p "
            "LEFT JOIN koptumbuh.referensi_koperasi_wilayah h ON h.koperasi_ref=p.koperasi_ref "
            "LEFT JOIN koptumbuh.referensi_wilayah w ON w.kode_wilayah=h.kode_wilayah "
            "WHERE p.koperasi_ref=:ref"
        ),
        {"ref": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    return ApiResponse(
        data={
            "koperasi_ref": row[0],
            "nama_koperasi": row[1],
            "status_registrasi": row[2],
            "bentuk_koperasi": row[3],
            "kategori_usaha": row[4],
            "nik_koperasi": row[5],
            "alamat_lengkap": row[6],
            "kode_pos": row[7],
            "koordinat": row[8],
            "modal_awal": row[9],
            "sumber_persetujuan": row[10],
            "tentang_koperasi": row[11],
            "pola_pengelolaan": row[12],
            "metode_pengisian": row[13],
            "kode_wilayah": row[14],
            "wilayah": {
                "provinsi": row[15],
                "kab_kota": row[16],
                "kecamatan": row[17],
                "desa_kelurahan": row[18],
            },
        }
    )


async def _list_child(db: AsyncSession, sql: str, ref: str, mapper):
    result = await db.execute(text(sql), {"ref": ref})
    return [mapper(r) for r in result.fetchall()]


@router.get("/cooperatives/{ref}/outlets", response_model=ApiResponse)
async def cooperative_outlets(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT gerai_ref, jenis_gerai_ref, status_gerai, akses_internet, akses_listrik, "
        "jenis_bangunan, koordinat_dibulatkan FROM koptumbuh.gerai_koperasi WHERE koperasi_ref=:ref",
        ref,
        lambda r: {
            "gerai_ref": r[0],
            "jenis_gerai_ref": r[1],
            "status_gerai": r[2],
            "akses_internet": r[3],
            "akses_listrik": r[4],
            "jenis_bangunan": r[5],
            "koordinat": r[6],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/board", response_model=ApiResponse)
async def cooperative_board(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT pengurus_ref, nama, jabatan, status, no_hp, email, periode_mulai, periode_selesai "
        "FROM koptumbuh.pengurus_koperasi WHERE koperasi_ref=:ref ORDER BY jabatan",
        ref,
        lambda r: {
            "pengurus_ref": r[0],
            "nama": r[1],
            "jabatan": r[2],
            "status": r[3],
            "no_hp": r[4],
            "email": r[5],
            "periode_mulai": r[6],
            "periode_selesai": str(r[7]) if r[7] else None,
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/employees", response_model=ApiResponse)
async def cooperative_employees(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT karyawan_ref, nama, jabatan, nomor_hp_karyawan, email, status_karyawan, jenis_kelamin "
        "FROM koptumbuh.karyawan_koperasi WHERE koperasi_ref=:ref ORDER BY nama",
        ref,
        lambda r: {
            "karyawan_ref": r[0],
            "nama": r[1],
            "jabatan": r[2],
            "phone": r[3],
            "email": r[4],
            "status": r[5],
            "gender": r[6],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/assets", response_model=ApiResponse)
async def cooperative_assets(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT aset_ref, nama_aset, tipe_aset, status, luas_lahan, koordinat_dibulatkan "
        "FROM koptumbuh.aset_koperasi WHERE koperasi_ref=:ref",
        ref,
        lambda r: {
            "aset_ref": r[0],
            "nama_aset": r[1],
            "tipe_aset": r[2],
            "status": r[3],
            "luas_lahan": float(r[4]) if r[4] is not None else None,
            "koordinat": r[5],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/documents", response_model=ApiResponse)
async def cooperative_documents(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT d.dokumen_ref, d.jenis_dokumen_ref, rd.nama_dokumen, d.nomor, d.tanggal_berlaku, "
        "d.tanggal_kadaluarsa, d.unggahan_dokumen "
        "FROM koptumbuh.dokumen_koperasi d "
        "LEFT JOIN koptumbuh.referensi_dokumen_koperasi rd ON rd.jenis_dokumen_ref=d.jenis_dokumen_ref "
        "WHERE d.koperasi_ref=:ref",
        ref,
        lambda r: {
            "dokumen_ref": r[0],
            "jenis_dokumen_ref": r[1],
            "nama_dokumen": r[2],
            "nomor": r[3],
            "tanggal_berlaku": str(r[4]) if r[4] else None,
            "tanggal_kadaluarsa": str(r[5]) if r[5] else None,
            "unggahan": r[6],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/rat", response_model=ApiResponse)
async def cooperative_rat(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT rat_sample_id, tahun_buku, tanggal_rat, jumlah_peserta_rat, status_rat, tahap_rat, urutan_rat "
        "FROM koptumbuh.rat_koperasi WHERE koperasi_ref=:ref ORDER BY tahun_buku DESC",
        ref,
        lambda r: {
            "rat_sample_id": r[0],
            "tahun_buku": r[1],
            "tanggal_rat": str(r[2]) if r[2] else None,
            "jumlah_peserta": r[3],
            "status_rat": r[4],
            "tahap_rat": r[5],
            "urutan_rat": r[6],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/kbli", response_model=ApiResponse)
async def cooperative_kbli(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        'SELECT "__row_id", kode_kbli, nama_kbli, tipe_izin_usaha, tahun_kbli '
        "FROM koptumbuh.kbli_koperasi WHERE koperasi_ref=:ref",
        ref,
        lambda r: {
            "id": r[0],
            "kode_kbli": r[1],
            "nama_kbli": r[2],
            "tipe_izin_usaha": r[3],
            "tahun_kbli": r[4],
        },
    )
    return ApiResponse(data=data)


@router.get("/cooperatives/{ref}/capital", response_model=ApiResponse)
async def cooperative_capital(ref: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    if not _can_access(user, ref):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    data = await _list_child(
        db,
        "SELECT modal_ref, nomor_perjanjian, tipe_sumber, nama_sumber, tipe_modal, jumlah, tanggal_diterima "
        "FROM koptumbuh.modal_koperasi WHERE koperasi_ref=:ref ORDER BY tanggal_diterima DESC NULLS LAST",
        ref,
        lambda r: {
            "modal_ref": r[0],
            "nomor_perjanjian": r[1],
            "tipe_sumber": r[2],
            "nama_sumber": r[3],
            "tipe_modal": r[4],
            "jumlah": float(r[5] or 0),
            "tanggal_diterima": str(r[6]) if r[6] else None,
        },
    )
    return ApiResponse(data=data)
