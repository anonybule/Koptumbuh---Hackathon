from datetime import datetime, timedelta
import logging
from sqlalchemy import select, func
from app.workers.celery_app import celery_app
from app.models.koptumbuh import Rekomendasi, PemasokKoptumbuh
from app.models.products import ProdukKoperasi, InventarisProduk, BarangKeluarProduk
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

DEFAULT_LEAD_TIME = 3
BUFFER_DAYS = 2
ADS_WINDOW_DAYS = 14
SLOW_MOVING_DAYS = 30


@celery_app.task
def generate_all_recommendations(koperasi_ref: str = None):
    ref = koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_generate(ref))
    finally:
        loop.close()


async def _generate(koperasi_ref: str):
    logger.info("recommendations generate start: koperasi_ref=%s", koperasi_ref)
    async with AsyncSessionLocal() as db:
        recent = await db.execute(
            select(Rekomendasi.produk_sample_id, Rekomendasi.jenis).where(
                Rekomendasi.koperasi_ref == koperasi_ref,
                Rekomendasi.status.in_(["NEW", "READ"]),
                Rekomendasi.generated_at >= datetime.utcnow() - timedelta(hours=24),
            )
        )
        existing = {(r[0], r[1]) for r in recent.fetchall()}
        before = len(existing)

        supplier = (
            await db.execute(
                select(PemasokKoptumbuh)
                .where(
                    PemasokKoptumbuh.koperasi_ref == koperasi_ref,
                    PemasokKoptumbuh.status_aktif == True,  # noqa: E712
                )
                .order_by(PemasokKoptumbuh.lead_time_hari.asc().nullslast())
                .limit(1)
            )
        ).scalar_one_or_none()
        lead_time = (
            float(supplier.lead_time_hari)
            if supplier and supplier.lead_time_hari is not None
            else DEFAULT_LEAD_TIME
        )
        threshold = lead_time + BUFFER_DAYS
        since_ads = datetime.utcnow() - timedelta(days=ADS_WINDOW_DAYS)
        since_slow = datetime.utcnow() - timedelta(days=SLOW_MOVING_DAYS)

        products = (
            await db.execute(select(ProdukKoperasi).where(ProdukKoperasi.koperasi_ref == koperasi_ref))
        ).scalars().all()

        for p in products:
            inv = (
                await db.execute(
                    select(InventarisProduk).where(
                        InventarisProduk.produk_sample_id == p.produk_sample_id,
                        InventarisProduk.koperasi_ref == koperasi_ref,
                    )
                )
            ).scalar_one_or_none()
            stok = float(inv.stok or 0) if inv else 0.0

            sold_14 = (
                await db.execute(
                    select(func.coalesce(func.sum(BarangKeluarProduk.jumlah_keluar), 0)).where(
                        BarangKeluarProduk.produk_sample_id == p.produk_sample_id,
                        BarangKeluarProduk.koperasi_ref == koperasi_ref,
                        BarangKeluarProduk.tanggal_keluar >= since_ads,
                    )
                )
            ).scalar()
            ads = float(sold_14 or 0) / ADS_WINDOW_DAYS
            days_left = (stok / ads) if ads > 0 else None

            # STOCKOUT_RISK: active sales velocity and low days remaining
            if (p.produk_sample_id, "STOCKOUT_RISK") not in existing and ads > 0 and days_left is not None:
                if days_left <= threshold:
                    db.add(
                        Rekomendasi(
                            koperasi_ref=koperasi_ref,
                            jenis="STOCKOUT_RISK",
                            judul=f"Risiko habis: {p.nama_produk}",
                            isi_rekomendasi=(
                                f"Stok {stok:.0f}, ADS {ads:.1f}/hari. Tersisa ~{days_left:.1f} hari "
                                f"(ambang lead+buffer={threshold:.0f})."
                            ),
                            priority="HIGH" if days_left <= 2 else "MEDIUM",
                            produk_sample_id=p.produk_sample_id,
                            pemasok_id=supplier.pemasok_id if supplier else None,
                            generated_at=datetime.utcnow(),
                            explanation_payload={
                                "stock": stok,
                                "avg_daily_sales": ads,
                                "days_left": days_left,
                                "lead_time": lead_time,
                                "threshold": threshold,
                            },
                        )
                    )
                    existing.add((p.produk_sample_id, "STOCKOUT_RISK"))

            # RESTOCK: days_left <= lead+2 (same trigger, actionable order cue)
            if (p.produk_sample_id, "RESTOCK") not in existing and ads > 0 and days_left is not None:
                if days_left <= threshold:
                    suggested = max(0.0, (ads * threshold) - stok)
                    db.add(
                        Rekomendasi(
                            koperasi_ref=koperasi_ref,
                            jenis="RESTOCK",
                            judul=f"Restock {p.nama_produk}",
                            isi_rekomendasi=(
                                f"Pesan ~{suggested:.0f} unit. Stok {stok:.0f}, ADS {ads:.1f}/hari, "
                                f"sisa {days_left:.1f} hari ≤ lead+2 ({threshold:.0f})."
                            ),
                            priority="HIGH" if days_left <= lead_time else "MEDIUM",
                            produk_sample_id=p.produk_sample_id,
                            pemasok_id=supplier.pemasok_id if supplier else None,
                            generated_at=datetime.utcnow(),
                            explanation_payload={
                                "stock": stok,
                                "avg_daily_sales": ads,
                                "days_left": days_left,
                                "suggested_qty": suggested,
                                "lead_time": lead_time,
                            },
                        )
                    )
                    existing.add((p.produk_sample_id, "RESTOCK"))

            # SLOW_MOVING: no sales 30d + stock > 0
            if (p.produk_sample_id, "SLOW_MOVING") not in existing and stok > 0:
                recent_sales = (
                    await db.execute(
                        select(func.coalesce(func.sum(BarangKeluarProduk.jumlah_keluar), 0)).where(
                            BarangKeluarProduk.produk_sample_id == p.produk_sample_id,
                            BarangKeluarProduk.koperasi_ref == koperasi_ref,
                            BarangKeluarProduk.tanggal_keluar >= since_slow,
                        )
                    )
                ).scalar()
                if float(recent_sales or 0) == 0:
                    last_sale = (
                        await db.execute(
                            select(func.max(BarangKeluarProduk.tanggal_keluar)).where(
                                BarangKeluarProduk.produk_sample_id == p.produk_sample_id,
                                BarangKeluarProduk.koperasi_ref == koperasi_ref,
                            )
                        )
                    ).scalar()
                    db.add(
                        Rekomendasi(
                            koperasi_ref=koperasi_ref,
                            jenis="SLOW_MOVING",
                            judul=f"Lambat bergerak: {p.nama_produk}",
                            isi_rekomendasi=(
                                f"Stok {stok:.0f} tanpa penjualan 30 hari terakhir. "
                                f"Pertimbangkan promo atau bundling."
                            ),
                            priority="LOW",
                            produk_sample_id=p.produk_sample_id,
                            generated_at=datetime.utcnow(),
                            explanation_payload={
                                "stock": stok,
                                "days_without_sales": SLOW_MOVING_DAYS,
                                "last_sale": str(last_sale) if last_sale else None,
                            },
                        )
                    )
                    existing.add((p.produk_sample_id, "SLOW_MOVING"))

        await db.commit()
        logger.info(
            "recommendations generate done: koperasi_ref=%s new_pairs=%s",
            koperasi_ref,
            max(0, len(existing) - before),
        )


@celery_app.task
def generate_daily_briefing(koperasi_ref: str = None):
    """Generate daily operator briefing with key metrics and alerts."""
    ref = koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_briefing(ref))
    finally:
        loop.close()


async def _briefing(koperasi_ref: str):
    async with AsyncSessionLocal() as db:
        from sqlalchemy import text

        sales = (
            await db.execute(
                text(
                    "SELECT COALESCE(SUM(total_pembayaran),0), COUNT(*) "
                    "FROM koptumbuh.transaksi_penjualan "
                    "WHERE koperasi_ref=:r AND DATE(tanggal_dibuat)=CURRENT_DATE"
                ),
                {"r": koperasi_ref},
            )
        ).fetchone()
        stock = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.inventaris_produk "
                    "WHERE koperasi_ref=:r AND stok < 5"
                ),
                {"r": koperasi_ref},
            )
        ).scalar()
        credit = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan "
                    "WHERE koperasi_ref=:r AND status_transaksi='Unpaid'"
                ),
                {"r": koperasi_ref},
            )
        ).scalar()
        message = (
            f"Briefing Pagi\n"
            f"Penjualan hari ini: Rp {float(sales[0]):,.0f} ({sales[1]} tx)\n"
            f"Stok menipis: {stock} produk\n"
            f"Piutang: {credit} unpaid\n\n"
            f"Fokus hari ini: jual produk margin tertinggi!"
        )
        await db.execute(
            text(
                "INSERT INTO koptumbuh.notifikasi_log "
                "(koperasi_ref, channel, message_type, content, status) "
                "VALUES (:r, 'SYSTEM', 'SUMMARY', :m, 'QUEUED')"
            ),
            {"r": koperasi_ref, "m": message},
        )
        await db.commit()
