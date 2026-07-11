from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.api.deps import require_admin, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.config import settings
from app.services.export_service import generate_simkopdes_export, build_export_file

router = APIRouter(prefix="/admin", tags=["admin-export"])


@router.post("/export/simkopdes", response_model=ApiResponse)
async def export_simkopdes(body: dict | None = None, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    """
    Generate SIMKOPDES export of transactions for the cooperative.
    Uploads to MinIO; on MinIO failure still writes ekspor_log with local-path note.
    """
    body = body or {}
    ref = user["koperasi_ref"]
    fmt = (body.get("format") or "JSON").upper()
    if fmt not in ("JSON", "CSV", "XLSX"):
        raise HTTPException(status_code=422, detail="format must be JSON, CSV, or XLSX")
    export_type = body.get("export_type") or "TRANSAKSI"
    period_start = body.get("period_start")
    period_end = body.get("period_end")
    # Optional: generate all three formats when requested
    all_formats = body.get("all_formats") is True

    try:
        result = await generate_simkopdes_export(
            db,
            ref,
            fmt=fmt,
            export_type=export_type,
            period_start=period_start,
            period_end=period_end,
            pengguna_id=user.get("pengguna_id"),
            formats=["JSON", "CSV", "XLSX"] if all_formats else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build export file: {e}")

    if "exports" in result:
        return ApiResponse(data={
            "record_count": result["record_count"],
            "exports": result["exports"],
        })

    return ApiResponse(
        data={
            "ekspor_id": result["ekspor_id"],
            "format": result["format"],
            "record_count": result["record_count"],
            "file_url": result["file_url"],
            "status": result["status"],
            "filename": result["filename"],
            "storage": result.get("storage", "minio"),
        }
    )


@router.get("/export/history", response_model=ApiResponse)
async def export_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (
        await db.execute(
            text("SELECT COUNT(*) FROM koptumbuh.ekspor_log WHERE koperasi_ref=:r"),
            {"r": ref},
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            "SELECT ekspor_id, export_type, format, period_start, period_end, file_url, "
            "record_count, status, created_at, error_detail "
            "FROM koptumbuh.ekspor_log WHERE koperasi_ref=:r "
            "ORDER BY created_at DESC NULLS LAST OFFSET :off LIMIT :lim"
        ),
        {"r": ref, "off": offset, "lim": limit},
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "export_type": r[1],
                "format": r[2],
                "period_start": str(r[3]) if r[3] else None,
                "period_end": str(r[4]) if r[4] else None,
                "file_url": r[5],
                "record_count": r[6],
                "status": r[7],
                "created_at": str(r[8]) if r[8] else None,
                "error_detail": r[9],
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/export/download/{id}")
async def export_download(id: str, user: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text(
            "SELECT ekspor_id, format, file_url, status, koperasi_ref, export_type, created_at "
            "FROM koptumbuh.ekspor_log WHERE ekspor_id=:id AND koperasi_ref=:r"
        ),
        {"id": id, "r": user["koperasi_ref"]},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Export not found")
    if row[3] == "FAILED":
        raise HTTPException(status_code=400, detail="Export failed; nothing to download")

    fmt = (row[1] or "JSON").upper()
    file_url = row[2] or ""
    content_types = {
        "JSON": "application/json",
        "CSV": "text/csv",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    content_type = content_types.get(fmt, "application/octet-stream")
    filename = f"export_{id}.{fmt.lower()}"

    if file_url and not file_url.startswith("local://"):
        try:
            from app.services.minio_service import download_bytes

            if file_url.startswith(settings.MINIO_BUCKET_EXPORTS + "/"):
                key = file_url[len(settings.MINIO_BUCKET_EXPORTS) + 1 :]
                bucket = settings.MINIO_BUCKET_EXPORTS
            elif "/" in file_url:
                bucket, key = file_url.split("/", 1)
            else:
                bucket, key = settings.MINIO_BUCKET_EXPORTS, file_url
            data = download_bytes(bucket, key)
            return Response(
                content=data,
                media_type=content_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception:
            pass

    tx = await db.execute(
        text(
            "SELECT transaksi_sample_id, nama_pelanggan, total_pembayaran, status_transaksi, "
            "metode_pembayaran, tanggal_dibuat, koperasi_ref "
            "FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r "
            "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
            "ORDER BY tanggal_dibuat"
        ),
        {"r": user["koperasi_ref"]},
    )
    rows = [
        {
            "transaksi_sample_id": r[0],
            "nama_pelanggan": r[1],
            "total_pembayaran": float(r[2] or 0),
            "status_transaksi": r[3],
            "metode_pembayaran": r[4],
            "tanggal_dibuat": str(r[5]) if r[5] else None,
            "koperasi_ref": r[6],
        }
        for r in tx.fetchall()
    ]
    content, content_type = build_export_file(rows, fmt)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/mappings", response_model=ApiResponse)
async def list_export_mappings(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str | None = Query(None, description="EXPORTED | SYNCED | PENDING"),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """SIMKOPDES mapping trail — EXPORTED after file gen; SYNCED = simulated Dinas accept."""
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["koperasi_ref=:r", "local_table='transaksi_penjualan'"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if status:
        where.append("mapping_status=:st")
        params["st"] = status
    clause = " AND ".join(where)
    total = (
        await db.execute(
            text(f"SELECT COUNT(*) FROM koptumbuh.mapping_integrasi WHERE {clause}"),
            params,
        )
    ).scalar() or 0
    result = await db.execute(
        text(
            f"SELECT mapping_id, local_id, external_table, external_reference, "
            f"mapping_status, last_exported_at, created_at, updated_at "
            f"FROM koptumbuh.mapping_integrasi WHERE {clause} "
            f"ORDER BY COALESCE(last_exported_at, created_at) DESC NULLS LAST "
            f"OFFSET :off LIMIT :lim"
        ),
        params,
    )
    return ApiResponse(
        data=[
            {
                "id": str(r[0]),
                "transaksi_sample_id": r[1],
                "external_table": r[2],
                "ekspor_id": r[3],
                "status": r[4],
                "last_exported_at": str(r[5]) if r[5] else None,
                "created_at": str(r[6]) if r[6] else None,
                "updated_at": str(r[7]) if r[7] else None,
            }
            for r in result.fetchall()
        ],
        meta=paginate(page, per_page, total),
    )


@router.post("/export/mappings/{mapping_id}/accept", response_model=ApiResponse)
async def accept_export_mapping(
    mapping_id: str,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark mapping as SYNCED — simulated Dinas/SIMKOPDES acceptance (not a live gov writeback).
    """
    result = await db.execute(
        text(
            "UPDATE koptumbuh.mapping_integrasi "
            "SET mapping_status='SYNCED', updated_at=NOW() "
            "WHERE mapping_id=:id AND koperasi_ref=:r AND mapping_status='EXPORTED' "
            "RETURNING mapping_id, local_id, mapping_status"
        ),
        {"id": mapping_id, "r": user["koperasi_ref"]},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Mapping not found or not in EXPORTED status",
        )
    await db.commit()
    return ApiResponse(
        data={
            "id": str(row[0]),
            "transaksi_sample_id": row[1],
            "status": row[2],
            "note": "Simulasi penerimaan Dinas — bukan writeback live ke SIMKOPDES",
        }
    )


@router.post("/export/mappings/accept-all", response_model=ApiResponse)
async def accept_all_exported(
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Bulk mark all EXPORTED mappings as SYNCED (demo acceptance)."""
    result = await db.execute(
        text(
            "UPDATE koptumbuh.mapping_integrasi "
            "SET mapping_status='SYNCED', updated_at=NOW() "
            "WHERE koperasi_ref=:r AND mapping_status='EXPORTED' "
            "AND local_table='transaksi_penjualan' "
            "RETURNING mapping_id"
        ),
        {"r": user["koperasi_ref"]},
    )
    ids = [str(r[0]) for r in result.fetchall()]
    await db.commit()
    return ApiResponse(
        data={
            "accepted_count": len(ids),
            "ids": ids,
            "note": "Simulasi penerimaan Dinas — bukan writeback live ke SIMKOPDES",
        }
    )
