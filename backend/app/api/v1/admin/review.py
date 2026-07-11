"""Web Tinjau — approve/reject pending WhatsApp parses into the ledger."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.database import get_db
from app.api.deps import require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit
from app.models.koptumbuh import PesanMasuk, ParsingPesan, PenggunaKoptumbuh
from app.services.state_machine import commit_transaction

router = APIRouter(prefix="/admin", tags=["admin-review"])


@router.get("/review/pending", response_model=ApiResponse)
async def list_pending_review(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Pesan awaiting YA (PARSED) or operator fix (NEEDS_REVIEW)."""
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    total = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM koptumbuh.pesan_masuk "
                "WHERE koperasi_ref=:r AND status IN ('PARSED','NEEDS_REVIEW')"
            ),
            {"r": ref},
        )
    ).scalar() or 0
    rows = (
        await db.execute(
            text(
                """
                SELECT m.pesan_id, m.input_type, m.raw_text, m.status, m.received_at,
                       p.parsing_id, p.detected_intent, p.extracted_payload,
                       p.confidence_score, p.validation_errors, p.status AS parsing_status,
                       u.nama
                FROM koptumbuh.pesan_masuk m
                LEFT JOIN LATERAL (
                    SELECT * FROM koptumbuh.parsing_pesan pp
                    WHERE pp.pesan_id = m.pesan_id
                    ORDER BY pp.created_at DESC LIMIT 1
                ) p ON TRUE
                LEFT JOIN koptumbuh.pengguna_koptumbuh u ON u.pengguna_id = m.pengguna_id
                WHERE m.koperasi_ref=:r AND m.status IN ('PARSED','NEEDS_REVIEW')
                ORDER BY m.received_at DESC
                OFFSET :off LIMIT :lim
                """
            ),
            {"r": ref, "off": offset, "lim": limit},
        )
    ).fetchall()

    data = []
    for r in rows:
        payload = r[7] or {}
        resolved = payload.get("resolved_items") or []
        unmatched = payload.get("unmatched") or []
        data.append(
            {
                "pesan_id": str(r[0]),
                "input_type": r[1],
                "raw_text": r[2],
                "status": r[3],
                "received_at": str(r[4]) if r[4] else None,
                "parsing_id": str(r[5]) if r[5] else None,
                "intent": r[6],
                "payload": payload,
                "confidence": float(r[8]) if r[8] is not None else None,
                "validation_errors": r[9] or [],
                "parsing_status": r[10],
                "operator_name": r[11],
                "line_count": len(resolved),
                "unmatched_count": len(unmatched) if isinstance(unmatched, list) else 0,
                "calculated_total": payload.get("calculated_total"),
                "can_approve": bool(resolved) and r[3] in ("PARSED", "NEEDS_REVIEW"),
            }
        )
    return ApiResponse(data=data, meta=paginate(page, per_page, total))


@router.post("/review/{pesan_id}/approve", response_model=ApiResponse)
async def approve_pending(
    pesan_id: UUID,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Commit pending parse to ledger (web YA) — prices already from DB."""
    ref = user["koperasi_ref"]
    pesan = (
        await db.execute(
            select(PesanMasuk).where(
                PesanMasuk.pesan_id == pesan_id,
                PesanMasuk.koperasi_ref == ref,
            )
        )
    ).scalar_one_or_none()
    if not pesan:
        raise HTTPException(status_code=404, detail="Pesan not found")
    if pesan.status not in ("PARSED", "NEEDS_REVIEW"):
        raise HTTPException(status_code=400, detail=f"Cannot approve status {pesan.status}")

    parsing = (
        await db.execute(
            select(ParsingPesan)
            .where(ParsingPesan.pesan_id == pesan_id)
            .order_by(ParsingPesan.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if not parsing:
        raise HTTPException(status_code=400, detail="No parsing for this pesan")

    payload = parsing.extracted_payload or {}
    if not payload.get("resolved_items"):
        raise HTTPException(
            status_code=400,
            detail="Tidak ada item ter-resolve — perbaiki via WhatsApp UBAH atau POS",
        )

    owner = (
        await db.execute(
            select(PenggunaKoptumbuh).where(PenggunaKoptumbuh.pengguna_id == pesan.pengguna_id)
        )
    ).scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="Operator pemilik pesan tidak ditemukan")

    try:
        await commit_transaction(parsing, pesan, owner, db)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    # Tag sumber as TINJAU if still WHATSAPP from commit — update to TINJAU for audit clarity
    tx_row = (
        await db.execute(
            text(
                "SELECT transaksi_sample_id FROM koptumbuh.transaksi_sumber "
                "WHERE pesan_id=:p ORDER BY created_at DESC LIMIT 1"
            ),
            {"p": pesan_id},
        )
    ).fetchone()
    if tx_row:
        await db.execute(
            text(
                "UPDATE koptumbuh.transaksi_sumber SET sumber='TINJAU' "
                "WHERE transaksi_sample_id=:tx"
            ),
            {"tx": tx_row[0]},
        )
        await db.commit()
        return ApiResponse(
            data={
                "pesan_id": str(pesan_id),
                "transaksi_sample_id": tx_row[0],
                "status": "CONFIRMED",
            }
        )

    return ApiResponse(data={"pesan_id": str(pesan_id), "status": "CONFIRMED"})


@router.post("/review/{pesan_id}/reject", response_model=ApiResponse)
async def reject_pending(
    pesan_id: UUID,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Cancel pending pesan (web BATAL)."""
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "UPDATE koptumbuh.pesan_masuk SET status='CANCELLED', processed_at=NOW() "
            "WHERE pesan_id=:id AND koperasi_ref=:r AND status IN ('PARSED','NEEDS_REVIEW') "
            "RETURNING pesan_id"
        ),
        {"id": pesan_id, "r": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pesan not found or not pending")
    await db.execute(
        text(
            "UPDATE koptumbuh.parsing_pesan SET status='SUPERSEDED' "
            "WHERE pesan_id=:id AND status IN ('DRAFT','VALID','INVALID')"
        ),
        {"id": pesan_id},
    )
    await db.commit()
    return ApiResponse(data={"pesan_id": str(pesan_id), "status": "CANCELLED"})
