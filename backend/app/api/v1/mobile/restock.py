import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import get_current_user, require_operator, require_admin
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.services.normalize import normalize_payment, normalize_unit

router = APIRouter(prefix="/mobile", tags=["mobile"])


class RestockBody(BaseModel):
    produk_sample_id: str
    jumlah_masuk: float = Field(gt=0)
    harga_beli: float = Field(ge=0)
    harga_jual: float = Field(ge=0)
    nama_produk: str | None = None


@router.get("/restock", response_model=ApiResponse)
async def list_restock(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (await db.execute(
        text("SELECT COUNT(*) FROM koptumbuh.barang_masuk_produk WHERE koperasi_ref=:ref"),
        {"ref": ref},
    )).scalar() or 0

    rows = (await db.execute(
        text(
            "SELECT barang_masuk_ref, produk_sample_id, nama_produk, jumlah_masuk, "
            "harga_beli, harga_jual, status, tanggal_masuk "
            "FROM koptumbuh.barang_masuk_produk WHERE koperasi_ref=:ref "
            "ORDER BY tanggal_masuk DESC OFFSET :offset LIMIT :limit"
        ),
        {"ref": ref, "offset": offset, "limit": limit},
    )).fetchall()

    return ApiResponse(
        data=[
            {
                "id": r[0],
                "produk_sample_id": r[1],
                "nama_produk": r[2],
                "qty": float(r[3] or 0),
                "harga_beli": float(r[4] or 0),
                "harga_jual": float(r[5] or 0),
                "status": r[6],
                "date": str(r[7]) if r[7] else None,
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/restock", response_model=ApiResponse)
async def create_restock(
    body: RestockBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    prod = (await db.execute(
        text(
            "SELECT nama_produk, kode_barcode FROM koptumbuh.produk_koperasi "
            "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
        ),
        {"pid": body.produk_sample_id, "ref": ref},
    )).fetchone()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    nama = body.nama_produk or prod[0]
    bm_id = f"BM-{uuid.uuid4().hex[:12].upper()}"
    total_biaya = body.harga_beli * body.jumlah_masuk

    await db.execute(
        text(
            "INSERT INTO koptumbuh.barang_masuk_produk "
            "(barang_masuk_ref, produk_sample_id, koperasi_ref, kode_barcode, nama_produk, "
            " jumlah_masuk, jumlah_tersedia, harga_beli, harga_jual, total_biaya, "
            " status, tanggal_masuk) "
            "VALUES (:id, :pid, :ref, :barcode, :nama, :qty, :qty, :beli, :jual, :total, "
            " 'Diterima', NOW())"
        ),
        {
            "id": bm_id,
            "pid": body.produk_sample_id,
            "ref": ref,
            "barcode": prod[1],
            "nama": nama,
            "qty": body.jumlah_masuk,
            "beli": body.harga_beli,
            "jual": body.harga_jual,
            "total": total_biaya,
        },
    )

    updated = await db.execute(
        text(
            "UPDATE koptumbuh.inventaris_produk "
            "SET stok = COALESCE(stok, 0) + :qty, diperbarui_pada = NOW() "
            "WHERE produk_sample_id=:pid AND koperasi_ref=:ref"
        ),
        {"qty": body.jumlah_masuk, "pid": body.produk_sample_id, "ref": ref},
    )
    if updated.rowcount == 0:
        inv_id = f"INV-{uuid.uuid4().hex[:12].upper()}"
        await db.execute(
            text(
                "INSERT INTO koptumbuh.inventaris_produk "
                "(inventaris_ref, produk_sample_id, koperasi_ref, nama_produk, stok, kode_barcode) "
                "VALUES (:id, :pid, :ref, :nama, :qty, :barcode)"
            ),
            {
                "id": inv_id,
                "pid": body.produk_sample_id,
                "ref": ref,
                "nama": nama,
                "qty": body.jumlah_masuk,
                "barcode": prod[1],
            },
        )

    await db.commit()
    return ApiResponse(data={
        "id": bm_id,
        "produk_sample_id": body.produk_sample_id,
        "nama_produk": nama,
        "qty": body.jumlah_masuk,
        "harga_beli": body.harga_beli,
        "harga_jual": body.harga_jual,
        "total_biaya": total_biaya,
    })
