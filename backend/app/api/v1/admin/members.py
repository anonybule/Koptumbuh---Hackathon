from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-members"])


@router.get("/members", response_model=ApiResponse)
async def list_members(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    q: str | None = None,
    koperasi_ref: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset, limit = offset_limit(page, per_page)
    where = ["1=1"]
    params: dict = {"off": offset, "lim": limit}

    # Pembina/ADMIN can query across cooperatives; others scoped to own
    if user["role"] in ("PEMBINA", "ADMIN") and koperasi_ref:
        where.append("a.koperasi_ref=:r")
        params["r"] = koperasi_ref
    elif user["role"] not in ("PEMBINA", "ADMIN"):
        where.append("a.koperasi_ref=:r")
        params["r"] = user["koperasi_ref"]
    elif koperasi_ref:
        where.append("a.koperasi_ref=:r")
        params["r"] = koperasi_ref

    if q:
        where.append("(a.nama ILIKE :q OR a.nik ILIKE :q OR a.anggota_ref ILIKE :q)")
        params["q"] = f"%{q}%"
    clause = " AND ".join(where)

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM koptumbuh.anggota_koperasi a WHERE {clause}"), params)
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT a.anggota_ref, a.nama, a.jenis_kelamin, a.status_keanggotaan, a.tanggal_terdaftar, "
            f"a.koperasi_ref, a.nik, a.pekerjaan "
            f"FROM koptumbuh.anggota_koperasi a WHERE {clause} "
            f"ORDER BY a.tanggal_terdaftar DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "name": r[1],
                "gender": r[2],
                "status": r[3],
                "registered": str(r[4]) if r[4] else None,
                "koperasi_ref": r[5],
                "nik": r[6],
                "pekerjaan": r[7],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/members/{id}", response_model=ApiResponse)
async def member_detail(id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    params = {"id": id}
    scope = ""
    if user["role"] not in ("PEMBINA", "ADMIN"):
        scope = " AND koperasi_ref=:r"
        params["r"] = user["koperasi_ref"]

    result = await db.execute(
        text(
            f"SELECT anggota_ref, nama, nik, jenis_kelamin, status_keanggotaan, tanggal_terdaftar, "
            f"koperasi_ref, pekerjaan, status_akun, kode_wilayah "
            f"FROM koptumbuh.anggota_koperasi WHERE anggota_ref=:id{scope}"
        ),
        params,
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")

    savings = await db.execute(
        text(
            "SELECT simpanan_ref, periode_pembayaran, jumlah_simpanan, status, dibuat_pada, dibayar_pada "
            "FROM koptumbuh.simpanan_anggota WHERE anggota_ref=:id ORDER BY dibuat_pada DESC LIMIT 50"
        ),
        {"id": id},
    )
    activity = await db.execute(
        text(
            "SELECT t.transaksi_sample_id, t.total_pembayaran, t.status_transaksi, t.tanggal_dibuat, t.metode_pembayaran "
            "FROM koptumbuh.relasi_transaksi_pihak r "
            "JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
            "WHERE r.anggota_ref=:id ORDER BY t.tanggal_dibuat DESC LIMIT 50"
        ),
        {"id": id},
    )
    sav_rows = savings.fetchall()
    return ApiResponse(
        data={
            "id": row[0],
            "name": row[1],
            "nik": row[2],
            "gender": row[3],
            "status": row[4],
            "registered": str(row[5]) if row[5] else None,
            "koperasi_ref": row[6],
            "pekerjaan": row[7],
            "status_akun": row[8],
            "kode_wilayah": row[9],
            "savings_total": float(sum(float(s[2] or 0) for s in sav_rows)),
            "savings": [
                {
                    "simpanan_ref": s[0],
                    "periode": s[1],
                    "jumlah": float(s[2] or 0),
                    "status": s[3],
                    "created": str(s[4]) if s[4] else None,
                    "paid": str(s[5]) if s[5] else None,
                }
                for s in sav_rows
            ],
            "activity": [
                {
                    "transaksi_sample_id": a[0],
                    "total": float(a[1] or 0),
                    "status": a[2],
                    "date": str(a[3]) if a[3] else None,
                    "method": a[4],
                }
                for a in activity.fetchall()
            ],
        }
    )
