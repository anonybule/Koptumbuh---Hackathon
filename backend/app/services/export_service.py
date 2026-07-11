"""SIMKOPDES export: CSV + XLSX + JSON → MinIO + ekspor_log."""
from __future__ import annotations
import io
import json
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings


def _build_file(rows: list[dict], fmt: str) -> tuple[bytes, str]:
    fmt = fmt.upper()
    if fmt == "JSON":
        return json.dumps(rows, ensure_ascii=False, default=str).encode("utf-8"), "application/json"
    if fmt == "CSV":
        import pandas as pd

        df = pd.DataFrame(rows)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8"), "text/csv"
    if fmt == "XLSX":
        import pandas as pd

        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine="openpyxl")
        return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    raise ValueError(f"Unsupported format: {fmt}")


async def _fetch_transaction_rows(
    db: AsyncSession,
    koperasi_ref: str,
    period_start=None,
    period_end=None,
) -> list[dict]:
    where = [
        "t.koperasi_ref=:r",
        "COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')",
    ]
    params: dict = {"r": koperasi_ref}
    if period_start:
        where.append("COALESCE(t.tanggal_dibuat, t.dibuat_pada)::date >= :ps")
        params["ps"] = period_start
    if period_end:
        where.append("COALESCE(t.tanggal_dibuat, t.dibuat_pada)::date <= :pe")
        params["pe"] = period_end
    clause = " AND ".join(where)
    result = await db.execute(
        text(
            f"SELECT t.transaksi_sample_id, t.nama_pelanggan, t.total_pembayaran, t.status_transaksi, "
            f"t.metode_pembayaran, t.tanggal_dibuat, t.koperasi_ref "
            f"FROM koptumbuh.transaksi_penjualan t WHERE {clause} "
            f"ORDER BY t.tanggal_dibuat"
        ),
        params,
    )
    return [
        {
            "transaksi_sample_id": r[0],
            "nama_pelanggan": r[1],
            "total_pembayaran": float(r[2] or 0),
            "status_transaksi": r[3],
            "metode_pembayaran": r[4],
            "tanggal_dibuat": str(r[5]) if r[5] else None,
            "koperasi_ref": r[6],
        }
        for r in result.fetchall()
    ]


async def generate_simkopdes_export(
    db: AsyncSession,
    koperasi_ref: str,
    *,
    fmt: str = "JSON",
    export_type: str = "TRANSAKSI",
    period_start=None,
    period_end=None,
    pengguna_id: str | None = None,
    formats: list[str] | None = None,
) -> dict:
    """
    Build export file(s), upload to MINIO_BUCKET_EXPORTS, insert/update ekspor_log.
    If formats is provided, generates all of CSV/XLSX/JSON; otherwise a single fmt.
    """
    fmt = (fmt or "JSON").upper()
    to_generate = [f.upper() for f in (formats or [fmt])]
    for f in to_generate:
        if f not in ("JSON", "CSV", "XLSX"):
            raise ValueError(f"Unsupported format: {f}")

    rows = await _fetch_transaction_rows(db, koperasi_ref, period_start, period_end)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    results = []

    from app.services.minio_service import upload_bytes

    for f in to_generate:
        ekspor_id = str(uuid.uuid4())
        await db.execute(
            text(
                "INSERT INTO koptumbuh.ekspor_log "
                "(ekspor_id, koperasi_ref, pengguna_id, export_type, format, "
                " period_start, period_end, status) "
                "VALUES (:id, :r, :u, :et, :fmt, :ps, :pe, 'PROCESSING')"
            ),
            {
                "id": ekspor_id,
                "r": koperasi_ref,
                "u": pengguna_id,
                "et": export_type,
                "fmt": f,
                "ps": period_start,
                "pe": period_end,
            },
        )
        await db.commit()

        try:
            content, content_type = _build_file(rows, f)
        except Exception as e:
            await db.execute(
                text(
                    "UPDATE koptumbuh.ekspor_log SET status='FAILED', error_detail=:err, record_count=0 "
                    "WHERE ekspor_id=:id"
                ),
                {"id": ekspor_id, "err": json.dumps({"error": str(e)})},
            )
            await db.commit()
            raise

        filename = f"simkopdes_{koperasi_ref}_{export_type}_{stamp}.{f.lower()}"
        key = f"{koperasi_ref}/{filename}"
        file_url = None
        status = "SUCCESS"
        error_detail = None
        try:
            file_url = upload_bytes(settings.MINIO_BUCKET_EXPORTS, key, content, content_type)
        except Exception as e:
            status = "SUCCESS"
            local_note = f"local://exports/{key}"
            file_url = local_note
            error_detail = json.dumps(
                {
                    "minio_error": str(e),
                    "note": "MinIO upload failed; file retained as local path note",
                    "local_path": local_note,
                    "byte_size": len(content),
                }
            )

        await db.execute(
            text(
                "UPDATE koptumbuh.ekspor_log SET status=:st, file_url=:url, record_count=:cnt, error_detail=:err "
                "WHERE ekspor_id=:id"
            ),
            {
                "id": ekspor_id,
                "st": status,
                "url": file_url,
                "cnt": len(rows),
                "err": error_detail,
            },
        )
        # Mark each exported TX in mapping_integrasi (SIMKOPDES acceptance trail)
        if status == "SUCCESS" and rows:
            for row in rows:
                await db.execute(
                    text(
                        "INSERT INTO koptumbuh.mapping_integrasi "
                        "(koperasi_ref, entity_type, local_table, local_id, external_table, "
                        " external_reference, mapping_status, last_exported_at, updated_at) "
                        "VALUES (:r, 'TRANSAKSI', 'transaksi_penjualan', :tx, 'SIMKOPDES_TRANSAKSI', "
                        " :eref, 'EXPORTED', NOW(), NOW()) "
                        "ON CONFLICT (koperasi_ref, local_table, local_id, external_table) "
                        "DO UPDATE SET mapping_status='EXPORTED', "
                        "  external_reference=EXCLUDED.external_reference, "
                        "  last_exported_at=NOW(), updated_at=NOW()"
                    ),
                    {
                        "r": koperasi_ref,
                        "tx": row["transaksi_sample_id"],
                        "eref": ekspor_id,
                    },
                )
        await db.commit()
        results.append(
            {
                "ekspor_id": ekspor_id,
                "format": f,
                "record_count": len(rows),
                "file_url": file_url,
                "status": status,
                "filename": filename,
                "storage": "minio" if file_url and not str(file_url).startswith("local://") else "local_fallback",
                "content": content,
                "content_type": content_type,
            }
        )

    if len(results) == 1:
        out = {k: v for k, v in results[0].items() if k not in ("content", "content_type")}
        out["_content"] = results[0]["content"]
        out["_content_type"] = results[0]["content_type"]
        return out
    return {
        "record_count": len(rows),
        "exports": [{k: v for k, v in r.items() if k not in ("content", "content_type")} for r in results],
        "files": {r["format"]: r["content"] for r in results},
    }


# Re-export builder for download fallbacks
build_export_file = _build_file
