from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import get_current_user, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-finance"])


@router.get("/finance/bank-accounts", response_model=ApiResponse)
async def bank_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (
        await db.execute(
            text("SELECT COUNT(*) FROM koptumbuh.akun_bank_koperasi WHERE koperasi_ref=:r"),
            {"r": ref},
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            "SELECT akun_bank_ref, nama_rekening, nama_bank, dibuat_pada "
            "FROM koptumbuh.akun_bank_koperasi WHERE koperasi_ref=:r "
            "ORDER BY nama_bank OFFSET :off LIMIT :lim"
        ),
        {"r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "akun_bank_ref": r[0],
                "nama_rekening": r[1],
                "nama_bank": r[2],
                "created": str(r[3]) if r[3] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/finance/capital", response_model=ApiResponse)
async def capital(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (
        await db.execute(
            text("SELECT COUNT(*) FROM koptumbuh.modal_koperasi WHERE koperasi_ref=:r"),
            {"r": ref},
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            "SELECT modal_ref, nomor_perjanjian, tipe_sumber, nama_sumber, tipe_modal, jumlah, tanggal_diterima "
            "FROM koptumbuh.modal_koperasi WHERE koperasi_ref=:r "
            "ORDER BY tanggal_diterima DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        {"r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "modal_ref": r[0],
                "nomor_perjanjian": r[1],
                "tipe_sumber": r[2],
                "nama_sumber": r[3],
                "tipe_modal": r[4],
                "jumlah": float(r[5] or 0),
                "tanggal_diterima": str(r[6]) if r[6] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/applications/bank-account", response_model=ApiResponse)
async def applications_bank_account(
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT pengajuan_rekening_ref, nik, penanggung_jawab, nomor_penanggung_jawab, "
            "status, kode_bank, nama_bank, dibuat_pada "
            "FROM koptumbuh.pengajuan_rekening_bank WHERE koperasi_ref=:r ORDER BY dibuat_pada DESC"
        ),
        {"r": ref},
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "nik": r[1],
                "penanggung_jawab": r[2],
                "nomor_penanggung_jawab": r[3],
                "status": r[4],
                "kode_bank": r[5],
                "nama_bank": r[6],
                "created": str(r[7]) if r[7] else None,
            }
            for r in result.fetchall()
        ]
    )


@router.get("/applications/financing", response_model=ApiResponse)
async def applications_financing(user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT pengajuan_pembiayaan_ref, nik, penanggung_jawab, nomor_penanggung_jawab, "
            "status_permohonan, nominal_permohonan, tenor, tujuan_permohonan, dibuat_pada "
            "FROM koptumbuh.pengajuan_pembiayaan WHERE koperasi_ref=:r ORDER BY dibuat_pada DESC"
        ),
        {"r": ref},
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "nik": r[1],
                "penanggung_jawab": r[2],
                "nomor_penanggung_jawab": r[3],
                "status": r[4],
                "nominal": float(r[5] or 0),
                "tenor": r[6],
                "tujuan": r[7],
                "created": str(r[8]) if r[8] else None,
            }
            for r in result.fetchall()
        ]
    )


@router.get("/applications/partnership", response_model=ApiResponse)
async def applications_partnership(user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT pengajuan_kemitraan_ref, nik, penanggung_jawab, nomor_penanggung_jawab, "
            "status_permohonan, bisnis_kemitraan, paket_kemitraan, tipe_kemitraan, catatan, dibuat_pada "
            "FROM koptumbuh.pengajuan_kemitraan WHERE koperasi_ref=:r ORDER BY dibuat_pada DESC"
        ),
        {"r": ref},
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "nik": r[1],
                "penanggung_jawab": r[2],
                "nomor_penanggung_jawab": r[3],
                "status": r[4],
                "bisnis_kemitraan": r[5],
                "paket_kemitraan": r[6],
                "tipe_kemitraan": r[7],
                "catatan": r[8],
                "created": str(r[9]) if r[9] else None,
            }
            for r in result.fetchall()
        ]
    )


@router.get("/applications/domain", response_model=ApiResponse)
async def applications_domain(user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "SELECT domain_ref, domain_koperasi, status_verifikasi, status_domain, dibuat_pada "
            "FROM koptumbuh.pengajuan_domain WHERE koperasi_ref=:r ORDER BY dibuat_pada DESC"
        ),
        {"r": ref},
    )
    return ApiResponse(
        data=[
            {
                "id": r[0],
                "domain": r[1],
                "status_verifikasi": r[2],
                "status_domain": r[3],
                "created": str(r[4]) if r[4] else None,
            }
            for r in result.fetchall()
        ]
    )
