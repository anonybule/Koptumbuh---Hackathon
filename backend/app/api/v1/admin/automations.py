"""Admin APIs for scheduled automations and purchase orders."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse, paginate, offset_limit

router = APIRouter(prefix="/admin", tags=["admin-automations"])

# Catalog mirrors celery beat_schedule (Asia/Jakarta)
AUTOMATION_CATALOG = [
    {
        "id": "generate-recommendations",
        "task": "app.workers.recommendations.generate_all_recommendations",
        "title": "Generate rekomendasi stok",
        "description": "Hitung ADS & buat rekomendasi RESTOCK / STOCKOUT ke database.",
        "schedule": "Setiap 4 jam",
        "category": "supply",
        "result_href": "/recommendations",
    },
    {
        "id": "scrape-ecommerce-prices",
        "task": "app.workers.price_scraper.scrape_ecommerce_prices",
        "title": "Scrape harga pasar",
        "description": "Ambil perbandingan harga e-commerce (simulasi) untuk BI.",
        "schedule": "Setiap hari 06:00",
        "category": "bi",
        "result_href": "/analytics",
    },
    {
        "id": "morning-price-broadcast",
        "task": "app.workers.dispatcher.send_morning_broadcast",
        "title": "Broadcast harga pagi",
        "description": "Kirim ringkasan harga ke anggota via WhatsApp.",
        "schedule": "Setiap hari 07:00",
        "category": "whatsapp",
        "result_href": "/notifications",
    },
    {
        "id": "daily-operator-briefing",
        "task": "app.workers.recommendations.generate_daily_briefing",
        "title": "Briefing operator harian",
        "description": "Ringkas omzet hari ini, stok kritis, dan kredit untuk operator.",
        "schedule": "Setiap hari 07:15",
        "category": "ops",
        "result_href": "/notifications",
    },
    {
        "id": "auto-generate-purchase-orders",
        "task": "app.workers.supply_chain.auto_generate_po",
        "title": "Auto draft purchase order",
        "description": "Dari rencana restock ADS → buat PO status DRAFT per pemasok.",
        "schedule": "Setiap hari 07:30",
        "category": "supply",
        "result_href": "/supply",
    },
    {
        "id": "member-milestone-check",
        "task": "app.workers.relationship.check_member_milestones",
        "title": "Milestone anggota",
        "description": "Ucapkan selamat saat anggota mencapai milestone transaksi.",
        "schedule": "Setiap hari 08:00",
        "category": "relationship",
        "result_href": "/customer-relationship",
    },
    {
        "id": "winback-campaign",
        "task": "app.workers.relationship.run_winback_campaign",
        "title": "Kampanye win-back",
        "description": "WhatsApp ke anggota yang lama tidak belanja.",
        "schedule": "Setiap Senin 08:00",
        "category": "relationship",
        "result_href": "/customer-relationship",
    },
    {
        "id": "onboarding-check",
        "task": "app.workers.relationship.send_onboarding_messages",
        "title": "Onboarding anggota baru",
        "description": "Follow-up anggota baru yang belum transaksi pertama.",
        "schedule": "Setiap hari 09:00",
        "category": "relationship",
        "result_href": "/customer-relationship",
    },
    {
        "id": "daily-db-backup",
        "task": "app.workers.backup.run_backup",
        "title": "Backup database",
        "description": "Snapshot DB harian ke storage.",
        "schedule": "Setiap hari 02:00",
        "category": "ops",
        "result_href": "/settings",
    },
]


@router.get("/automations", response_model=ApiResponse)
async def list_automations(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    stats: dict = {
        "restock_items": 0,
        "draft_pos": 0,
        "open_recommendations": 0,
        "notifications_today": 0,
        "at_risk_members": 0,
    }

    try:
        from app.workers.supply_chain import compute_restock_plan

        plan = await compute_restock_plan(db, ref)
        stats["restock_items"] = len(plan)
    except Exception:
        await db.rollback()

    try:
        stats["draft_pos"] = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM koptumbuh.purchase_order "
                        "WHERE koperasi_ref=:r AND status='DRAFT'"
                    ),
                    {"r": ref},
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()

    try:
        stats["open_recommendations"] = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM koptumbuh.rekomendasi "
                        "WHERE koperasi_ref=:r AND status IN ('NEW','READ')"
                    ),
                    {"r": ref},
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()

    try:
        stats["notifications_today"] = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM koptumbuh.notifikasi_log "
                        "WHERE koperasi_ref=:r AND COALESCE(sent_at, created_at)::date = CURRENT_DATE"
                    ),
                    {"r": ref},
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()

    try:
        stats["at_risk_members"] = int(
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

    return ApiResponse(data={"jobs": AUTOMATION_CATALOG, "stats": stats})


@router.post("/automations/{job_id}/run", response_model=ApiResponse)
async def run_automation(job_id: str, user: dict = Depends(require_operator)):
    job = next((j for j in AUTOMATION_CATALOG if j["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown automation")

    ref = user["koperasi_ref"]
    task_path = job["task"]

    # Import and delay known tasks
    runners = {
        "app.workers.recommendations.generate_all_recommendations": lambda: __import__(
            "app.workers.recommendations", fromlist=["generate_all_recommendations"]
        ).generate_all_recommendations.delay(ref),
        "app.workers.price_scraper.scrape_ecommerce_prices": lambda: __import__(
            "app.workers.price_scraper", fromlist=["scrape_ecommerce_prices"]
        ).scrape_ecommerce_prices.delay(),
        "app.workers.dispatcher.send_morning_broadcast": lambda: __import__(
            "app.workers.dispatcher", fromlist=["send_morning_broadcast"]
        ).send_morning_broadcast.delay(ref),
        "app.workers.recommendations.generate_daily_briefing": lambda: __import__(
            "app.workers.recommendations", fromlist=["generate_daily_briefing"]
        ).generate_daily_briefing.delay(ref),
        "app.workers.supply_chain.auto_generate_po": lambda: __import__(
            "app.workers.supply_chain", fromlist=["auto_generate_po"]
        ).auto_generate_po.delay(ref),
        "app.workers.relationship.check_member_milestones": lambda: __import__(
            "app.workers.relationship", fromlist=["check_member_milestones"]
        ).check_member_milestones.delay(ref),
        "app.workers.relationship.run_winback_campaign": lambda: __import__(
            "app.workers.relationship", fromlist=["run_winback_campaign"]
        ).run_winback_campaign.delay(ref),
        "app.workers.relationship.send_onboarding_messages": lambda: __import__(
            "app.workers.relationship", fromlist=["send_onboarding_messages"]
        ).send_onboarding_messages.delay(ref),
        "app.workers.backup.run_backup": lambda: __import__(
            "app.workers.backup", fromlist=["run_backup"]
        ).run_backup.delay(),
    }

    runner = runners.get(task_path)
    if not runner:
        raise HTTPException(status_code=501, detail="Task not runnable from API")

    try:
        async_result = runner()
        task_id = getattr(async_result, "id", None)
    except Exception as e:
        # Celery/Redis may be down in local demo — run sync for PO & recs where possible
        if job_id == "auto-generate-purchase-orders":
            from app.workers.supply_chain import auto_generate_po

            result = auto_generate_po(ref)
            return ApiResponse(data={"status": "ran_sync", "job_id": job_id, "result": result, "error": str(e)})
        raise HTTPException(status_code=502, detail=f"Failed to queue job: {e}")

    return ApiResponse(data={"status": "queued", "job_id": job_id, "task_id": task_id})


@router.get("/purchase-orders", response_model=ApiResponse)
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: str | None = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    offset, limit = offset_limit(page, per_page)
    where = ["po.koperasi_ref=:r"]
    params: dict = {"r": ref, "off": offset, "lim": limit}
    if status:
        where.append("po.status=:st")
        params["st"] = status
    clause = " AND ".join(where)

    try:
        total = (
            await db.execute(
                text(f"SELECT COUNT(*) FROM koptumbuh.purchase_order po WHERE {clause}"),
                params,
            )
        ).scalar() or 0
        rows = (
            await db.execute(
                text(
                    f"SELECT po.po_id, po.status, po.tanggal_order, po.tanggal_estimasi, po.catatan, "
                    f"po.dibuat_pada, po.pemasok_id, s.nama_pemasok, "
                    f"(SELECT COUNT(*) FROM koptumbuh.purchase_order_item i WHERE i.po_id=po.po_id), "
                    f"(SELECT COALESCE(SUM(i.jumlah_dipesan * COALESCE(i.harga_per_unit,0)),0) "
                    f" FROM koptumbuh.purchase_order_item i WHERE i.po_id=po.po_id) "
                    f"FROM koptumbuh.purchase_order po "
                    f"LEFT JOIN koptumbuh.pemasok_koptumbuh s ON s.pemasok_id=po.pemasok_id "
                    f"WHERE {clause} ORDER BY po.dibuat_pada DESC NULLS LAST OFFSET :off LIMIT :lim"
                ),
                params,
            )
        ).fetchall()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=503, detail=f"purchase_order table unavailable: {e}")

    return ApiResponse(
        data=[
            {
                "po_id": str(r[0]),
                "status": r[1],
                "tanggal_order": str(r[2]) if r[2] else None,
                "tanggal_estimasi": str(r[3]) if r[3] else None,
                "catatan": r[4],
                "created_at": str(r[5]) if r[5] else None,
                "pemasok_id": str(r[6]) if r[6] else None,
                "supplier": r[7],
                "item_count": int(r[8] or 0),
                "total_estimasi": float(r[9] or 0),
            }
            for r in rows
        ],
        meta=paginate(page, per_page, total),
    )


@router.get("/purchase-orders/{po_id}", response_model=ApiResponse)
async def purchase_order_detail(
    po_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    row = (
        await db.execute(
            text(
                "SELECT po.po_id, po.status, po.tanggal_order, po.tanggal_estimasi, po.catatan, "
                "po.dibuat_pada, po.pemasok_id, s.nama_pemasok "
                "FROM koptumbuh.purchase_order po "
                "LEFT JOIN koptumbuh.pemasok_koptumbuh s ON s.pemasok_id=po.pemasok_id "
                "WHERE po.po_id=CAST(:id AS uuid) AND po.koperasi_ref=:r"
            ),
            {"id": po_id, "r": ref},
        )
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="PO not found")

    items = (
        await db.execute(
            text(
                "SELECT i.poi_id, i.produk_sample_id, p.nama_produk, i.jumlah_dipesan, "
                "i.jumlah_diterima, i.harga_per_unit "
                "FROM koptumbuh.purchase_order_item i "
                "LEFT JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id=i.produk_sample_id "
                "WHERE i.po_id=CAST(:id AS uuid) ORDER BY p.nama_produk"
            ),
            {"id": po_id},
        )
    ).fetchall()

    return ApiResponse(
        data={
            "po_id": str(row[0]),
            "status": row[1],
            "tanggal_order": str(row[2]) if row[2] else None,
            "tanggal_estimasi": str(row[3]) if row[3] else None,
            "catatan": row[4],
            "created_at": str(row[5]) if row[5] else None,
            "pemasok_id": str(row[6]) if row[6] else None,
            "supplier": row[7],
            "items": [
                {
                    "poi_id": str(i[0]),
                    "produk_sample_id": i[1],
                    "nama_produk": i[2] or i[1],
                    "jumlah_dipesan": float(i[3] or 0),
                    "jumlah_diterima": float(i[4] or 0),
                    "harga_per_unit": float(i[5] or 0) if i[5] is not None else None,
                }
                for i in items
            ],
        }
    )


class PoStatusBody(BaseModel):
    status: str = Field(..., pattern="^(DRAFT|DIKIRIM|DITERIMA_SEBAGIAN|DITERIMA|DIBATALKAN)$")


@router.patch("/purchase-orders/{po_id}", response_model=ApiResponse)
async def update_purchase_order(
    po_id: str,
    body: PoStatusBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    ref = user["koperasi_ref"]
    result = await db.execute(
        text(
            "UPDATE koptumbuh.purchase_order SET status=:st, diperbarui_pada=NOW() "
            "WHERE po_id=CAST(:id AS uuid) AND koperasi_ref=:r RETURNING po_id, status"
        ),
        {"st": body.status, "id": po_id, "r": ref},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="PO not found")
    await db.commit()
    return ApiResponse(data={"po_id": str(row[0]), "status": row[1]})
