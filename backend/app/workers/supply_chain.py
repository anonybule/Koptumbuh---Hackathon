"""Supply chain: ADS-based restock planning and auto PO generation."""
from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.workers.celery_app import celery_app
from app.models.products import ProdukKoperasi, InventarisProduk, BarangKeluarProduk, BarangMasukProduk
from app.models.koptumbuh import PemasokKoptumbuh
from app.database import AsyncSessionLocal

DEFAULT_LEAD_TIME = 3
BUFFER_DAYS = 2
ADS_WINDOW_DAYS = 14


async def compute_restock_plan(db: AsyncSession, koperasi_ref: str) -> list[dict]:
    """
    ADS = total qty sold in 14 days / 14.
    days_remaining = stok / ADS.
    Restock when days_remaining <= lead_time + 2 (default lead_time=3).
    """
    products = (
        await db.execute(select(ProdukKoperasi).where(ProdukKoperasi.koperasi_ref == koperasi_ref))
    ).scalars().all()

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
    lead_time = float(supplier.lead_time_hari) if supplier and supplier.lead_time_hari is not None else DEFAULT_LEAD_TIME
    threshold = lead_time + BUFFER_DAYS
    since = datetime.utcnow() - timedelta(days=ADS_WINDOW_DAYS)

    plan: list[dict] = []
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

        sold = (
            await db.execute(
                select(func.coalesce(func.sum(BarangKeluarProduk.jumlah_keluar), 0)).where(
                    BarangKeluarProduk.produk_sample_id == p.produk_sample_id,
                    BarangKeluarProduk.koperasi_ref == koperasi_ref,
                    BarangKeluarProduk.tanggal_keluar >= since,
                )
            )
        ).scalar()
        ads = float(sold or 0) / ADS_WINDOW_DAYS
        days_remaining = (stok / ads) if ads > 0 else None

        needs = (ads > 0 and days_remaining is not None and days_remaining <= threshold) or stok < 5
        if not needs:
            continue

        if ads > 0:
            suggested = max(0.0, (ads * threshold) - stok)
        else:
            suggested = 10.0 if stok < 5 else 0.0

        price_row = (
            await db.execute(
                select(BarangMasukProduk.harga_beli)
                .where(
                    BarangMasukProduk.produk_sample_id == p.produk_sample_id,
                    BarangMasukProduk.koperasi_ref == koperasi_ref,
                )
                .order_by(BarangMasukProduk.tanggal_masuk.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        plan.append({
            "produk_sample_id": p.produk_sample_id,
            "nama_produk": p.nama_produk,
            "stock": stok,
            "ads": round(ads, 4),
            "days_remaining": round(days_remaining, 2) if days_remaining is not None else None,
            "lead_time": lead_time,
            "threshold_days": threshold,
            "suggested_qty": round(suggested, 3),
            "harga_per_unit": float(price_row) if price_row else None,
            "pemasok_id": str(supplier.pemasok_id) if supplier else None,
            "supplier": supplier.nama_pemasok if supplier else None,
        })

    plan.sort(key=lambda x: (x["days_remaining"] is None, x["days_remaining"] or 0, x["stock"]))
    return plan


@celery_app.task
def auto_generate_po(koperasi_ref: str = None):
    ref = koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_auto_po(ref))
    finally:
        loop.close()


async def _auto_po(koperasi_ref: str):
    async with AsyncSessionLocal() as db:
        plan = await compute_restock_plan(db, koperasi_ref)
        orderable = [row for row in plan if row["suggested_qty"] > 0 and row["pemasok_id"]]
        if not orderable:
            return {"created": 0}

        # One DRAFT PO per supplier for items at/below lead+buffer
        by_supplier: dict[str, list] = {}
        for row in orderable:
            by_supplier.setdefault(row["pemasok_id"], []).append(row)

        created = 0
        for pemasok_id, items in by_supplier.items():
            lead = items[0]["lead_time"]
            po_result = await db.execute(
                text(
                    "INSERT INTO koptumbuh.purchase_order "
                    "(koperasi_ref, pemasok_id, status, tanggal_order, tanggal_estimasi, catatan) "
                    "VALUES (:r, CAST(:s AS uuid), 'DRAFT', CURRENT_DATE, "
                    "CURRENT_DATE + (:lead || ' days')::interval, :cat) "
                    "RETURNING po_id"
                ),
                {
                    "r": koperasi_ref,
                    "s": pemasok_id,
                    "lead": str(int(lead)),
                    "cat": "Auto-generated from ADS restock plan",
                },
            )
            po_id = po_result.scalar()
            for item in items:
                await db.execute(
                    text(
                        "INSERT INTO koptumbuh.purchase_order_item "
                        "(po_id, produk_sample_id, jumlah_dipesan, harga_per_unit) "
                        "VALUES (CAST(:po AS uuid), :pid, :qty, :harga)"
                    ),
                    {
                        "po": str(po_id),
                        "pid": item["produk_sample_id"],
                        "qty": item["suggested_qty"],
                        "harga": item["harga_per_unit"],
                    },
                )
            created += 1

        await db.commit()
        return {"created": created, "items": sum(len(v) for v in by_supplier.values())}
