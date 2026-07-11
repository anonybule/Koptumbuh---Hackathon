"""Ops pipeline APIs — inbox, health, campaign outcomes for the full-process UI."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from app.database import get_db
from app.config import settings
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin/ops", tags=["admin-ops"])


@router.get("/pipeline", response_model=ApiResponse)
async def ops_pipeline(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Counts for the WhatsApp → confirm → stock → PO → notify loop."""
    ref = user["koperasi_ref"]

    async def _count(sql: str, params: dict | None = None) -> int:
        try:
            return int((await db.execute(text(sql), params or {"r": ref})).scalar() or 0)
        except Exception:
            await db.rollback()
            return 0

    wa_in = await _count(
        "SELECT COUNT(*) FROM koptumbuh.pesan_masuk WHERE koperasi_ref=:r "
        "AND COALESCE(received_at, created_at)::date = CURRENT_DATE"
    )
    needs_review = await _count(
        "SELECT COUNT(*) FROM koptumbuh.pesan_masuk WHERE koperasi_ref=:r "
        "AND status IN ('NEEDS_REVIEW','RECEIVED')"
    )
    awaiting_ya = await _count(
        "SELECT COUNT(*) FROM koptumbuh.parsing_pesan p "
        "JOIN koptumbuh.pesan_masuk m ON m.pesan_id=p.pesan_id "
        "WHERE m.koperasi_ref=:r AND p.status='VALID'"
    )
    confirmed_today = await _count(
        "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan WHERE koperasi_ref=:r "
        "AND COALESCE(tanggal_dibuat, dibuat_pada)::date = CURRENT_DATE "
        "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')"
    )
    low_stock = await _count(
        "SELECT COUNT(*) FROM koptumbuh.inventaris_produk WHERE koperasi_ref=:r AND stok < 5"
    )
    draft_po = await _count(
        "SELECT COUNT(*) FROM koptumbuh.purchase_order WHERE koperasi_ref=:r AND status='DRAFT'"
    )
    open_recs = await _count(
        "SELECT COUNT(*) FROM koptumbuh.rekomendasi WHERE koperasi_ref=:r AND status IN ('NEW','READ')"
    )
    notif_today = await _count(
        "SELECT COUNT(*) FROM koptumbuh.notifikasi_log WHERE koperasi_ref=:r "
        "AND COALESCE(sent_at, created_at)::date = CURRENT_DATE"
    )

    stages = [
        {
            "id": "wa_in",
            "label": "WA masuk hari ini",
            "count": wa_in,
            "href": "/transactions?tab=inbox",
            "tone": "blue",
        },
        {
            "id": "review",
            "label": "Perlu review",
            "count": needs_review,
            "href": "/transactions?tab=inbox&status=NEEDS_REVIEW",
            "tone": "yellow",
        },
        {
            "id": "await_ya",
            "label": "Menunggu YA",
            "count": awaiting_ya,
            "href": "/transactions?tab=inbox&status=VALID",
            "tone": "yellow",
        },
        {
            "id": "confirmed",
            "label": "Transaksi hari ini",
            "count": confirmed_today,
            "href": "/transactions?tab=sales",
            "tone": "green",
        },
        {
            "id": "low_stock",
            "label": "Stok rendah",
            "count": low_stock,
            "href": "/inventory",
            "tone": "red",
        },
        {
            "id": "draft_po",
            "label": "PO draft",
            "count": draft_po,
            "href": "/supply",
            "tone": "blue",
        },
        {
            "id": "recs",
            "label": "Rekomendasi",
            "count": open_recs,
            "href": "/recommendations",
            "tone": "yellow",
        },
        {
            "id": "notif",
            "label": "Notif hari ini",
            "count": notif_today,
            "href": "/notifications",
            "tone": "green",
        },
    ]
    return ApiResponse(data={"stages": stages})


@router.get("/inbox", response_model=ApiResponse)
async def ops_inbox(
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    status: str | None = None,
    intent: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """WhatsApp pesan_masuk + latest parsing_pesan for the confirmation inbox."""
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["m.koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}

    if status:
        st = status.upper()
        if st in ("VALID", "DRAFT", "INVALID"):
            where.append("p.status=:pst")
            params["pst"] = st
        else:
            where.append("m.status=:mst")
            params["mst"] = st
    if intent:
        where.append("UPPER(COALESCE(p.detected_intent,'')) LIKE :intent")
        params["intent"] = f"%{intent.upper()}%"

    clause = " AND ".join(where)
    join = (
        "FROM koptumbuh.pesan_masuk m "
        "LEFT JOIN LATERAL ("
        "  SELECT * FROM koptumbuh.parsing_pesan pp "
        "  WHERE pp.pesan_id=m.pesan_id ORDER BY pp.created_at DESC NULLS LAST LIMIT 1"
        ") p ON TRUE "
        "LEFT JOIN koptumbuh.pengguna_koptumbuh u ON u.pengguna_id=m.pengguna_id "
    )

    try:
        total = (
            await db.execute(text(f"SELECT COUNT(*) {join} WHERE {clause}"), params)
        ).scalar() or 0
        rows = (
            await db.execute(
                text(
                    f"SELECT m.pesan_id, m.input_type, m.raw_text, m.status, m.received_at, "
                    f"m.whatsapp_message_id, u.nama, u.nomor_whatsapp, "
                    f"p.parsing_id, p.detected_intent, p.confidence_score, p.status, "
                    f"p.extracted_payload, p.validation_errors, p.transcription_text "
                    f"{join} WHERE {clause} "
                    f"ORDER BY m.received_at DESC NULLS LAST OFFSET :off LIMIT :lim"
                ),
                params,
            )
        ).fetchall()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=503, detail=f"Inbox unavailable: {e}")

    data = []
    for r in rows:
        payload = r[12] if isinstance(r[12], dict) else {}
        conf = float(r[10]) if r[10] is not None else None
        parse_status = r[11]
        msg_status = r[3]
        stage = "received"
        if parse_status == "VALID":
            stage = "awaiting_ya"
        elif parse_status == "DRAFT":
            stage = "parsing"
        elif parse_status == "INVALID" or msg_status == "NEEDS_REVIEW":
            stage = "needs_review"
        elif msg_status in ("PARSED", "PROCESSED", "CONFIRMED"):
            stage = "done"

        data.append(
            {
                "pesan_id": str(r[0]),
                "input_type": r[1],
                "raw_text": r[2] or r[14] or "",
                "message_status": msg_status,
                "received_at": str(r[4]) if r[4] else None,
                "whatsapp_message_id": r[5],
                "sender_name": r[6] or "Pengguna WA",
                "sender_phone": r[7],
                "parsing_id": str(r[8]) if r[8] else None,
                "intent": r[9],
                "confidence": conf,
                "parse_status": parse_status,
                "payload": payload,
                "validation_errors": r[13] if isinstance(r[13], list) else (r[13] or []),
                "stage": stage,
            }
        )

    return ApiResponse(data=data, meta=paginate(page, per_page, total))


@router.get("/health", response_model=ApiResponse)
async def ops_health(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    _ = user
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        await db.rollback()

    evo = {"ok": False, "state": "unknown", "instance": settings.EVOLUTION_INSTANCE}
    try:
        from app.services.whatsapp_service import whatsapp_service

        state = await whatsapp_service.connection_state()
        evo = {
            "ok": bool(state.get("success")),
            "state": state.get("state", "unknown"),
            "instance": state.get("instance") or settings.EVOLUTION_INSTANCE,
            "connected": str(state.get("state", "")).lower() in ("open", "connected", "online"),
            "error": state.get("error"),
        }
    except Exception as e:
        evo["error"] = str(e)

    redis_ok = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            # Redis isn't HTTP — probe Evolution or skip; use a cheap DB ping already done
            pass
        # Soft check via celery broker URL reachability is hard; mark unknown
        redis_ok = bool(settings.REDIS_URL)
    except Exception:
        redis_ok = False

    return ApiResponse(
        data={
            "database": {"ok": db_ok},
            "evolution": evo,
            "redis": {"configured": bool(settings.REDIS_URL), "url_set": redis_ok},
            "celery_jobs": 9,
            "api": {"ok": True, "version": "1.0.0"},
        }
    )


@router.get("/campaigns", response_model=ApiResponse)
async def ops_campaigns(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Relationship automation outcomes from notifikasi_log + retention risk counts."""
    ref = user["koperasi_ref"]

    types = [
        ("WINBACK", "winback", "Kampanye win-back"),
        ("ONBOARDING", "onboarding", "Onboarding anggota baru"),
        ("MILESTONE", "milestone", "Milestone transaksi"),
        ("BROADCAST", "broadcast", "Broadcast harga pagi"),
        ("BRIEFING", "briefing", "Briefing operator"),
        ("CONFIRMATION", "confirmation", "Konfirmasi YA"),
        ("ALERT", "alert", "Alert / review"),
    ]

    campaigns = []
    for mt, key, title in types:
        try:
            row = (
                await db.execute(
                    text(
                        "SELECT COUNT(*), MAX(COALESCE(sent_at, created_at)) "
                        "FROM koptumbuh.notifikasi_log "
                        "WHERE koperasi_ref=:r AND UPPER(COALESCE(message_type,'')) LIKE :mt"
                    ),
                    {"r": ref, "mt": f"%{mt}%"},
                )
            ).fetchone()
            # Also match by title/content keywords for loosely typed logs
            if not row or int(row[0] or 0) == 0:
                row = (
                    await db.execute(
                        text(
                            "SELECT COUNT(*), MAX(COALESCE(sent_at, created_at)) "
                            "FROM koptumbuh.notifikasi_log "
                            "WHERE koperasi_ref=:r AND ("
                            "  UPPER(COALESCE(title,'')) LIKE :mt "
                            "  OR UPPER(COALESCE(content,'')) LIKE :mt "
                            "  OR UPPER(COALESCE(message_type,'')) LIKE :mt"
                            ")"
                        ),
                        {"r": ref, "mt": f"%{key.upper()}%"},
                    )
                ).fetchone()
            campaigns.append(
                {
                    "id": key,
                    "title": title,
                    "message_type": mt,
                    "count": int(row[0] or 0) if row else 0,
                    "last_at": str(row[1]) if row and row[1] else None,
                }
            )
        except Exception:
            await db.rollback()
            campaigns.append(
                {"id": key, "title": title, "message_type": mt, "count": 0, "last_at": None}
            )

    at_risk = 0
    try:
        at_risk = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM ("
                        "  SELECT a.anggota_ref, "
                        "  CASE WHEN MAX(t.tanggal_dibuat) IS NULL THEN 999 "
                        "  ELSE (CURRENT_DATE - MAX(t.tanggal_dibuat)::date) END AS resensi "
                        "  FROM koptumbuh.anggota_koperasi a "
                        "  LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref "
                        "  LEFT JOIN koptumbuh.transaksi_penjualan t ON t.transaksi_sample_id=r.transaksi_sample_id "
                        "  WHERE a.koperasi_ref=:r GROUP BY a.anggota_ref"
                        ") x WHERE resensi > 60"
                    ),
                    {"r": ref},
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()

    recent = []
    try:
        rows = (
            await db.execute(
                text(
                    "SELECT notifikasi_id, message_type, title, content, status, "
                    "COALESCE(sent_at, created_at) "
                    "FROM koptumbuh.notifikasi_log WHERE koperasi_ref=:r "
                    "ORDER BY COALESCE(sent_at, created_at) DESC NULLS LAST LIMIT 20"
                ),
                {"r": ref},
            )
        ).fetchall()
        recent = [
            {
                "id": str(r[0]),
                "message_type": r[1],
                "title": r[2],
                "content": (r[3] or "")[:200],
                "status": r[4],
                "at": str(r[5]) if r[5] else None,
            }
            for r in rows
        ]
    except Exception:
        await db.rollback()

    return ApiResponse(data={"campaigns": campaigns, "at_risk_members": at_risk, "recent": recent})


class RecStatusBody(BaseModel):
    status: str = Field(..., pattern="^(NEW|READ|ACCEPTED|REJECTED|COMPLETED|EXPIRED)$")


@router.patch("/recommendations/{rec_id}", response_model=ApiResponse)
async def patch_recommendation_status(
    rec_id: str,
    body: RecStatusBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "UPDATE koptumbuh.rekomendasi SET status=:st "
            "WHERE rekomendasi_id=CAST(:id AS uuid) AND koperasi_ref=:r "
            "RETURNING rekomendasi_id, status, jenis, produk_sample_id"
        ),
        {"st": body.status, "id": rec_id, "r": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.commit()
    return ApiResponse(
        data={
            "id": str(row[0]),
            "status": row[1],
            "jenis": row[2],
            "produk_sample_id": row[3],
        }
    )
