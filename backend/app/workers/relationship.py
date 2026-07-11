"""Relationship engine: RFM tiers, milestones, winback, onboarding."""
from __future__ import annotations
from datetime import timedelta, date
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.workers.celery_app import celery_app
from app.models.members import AnggotaKoperasi
from app.models.koptumbuh import PenggunaKoptumbuh, PelangganKoptumbuh
from app.services.whatsapp_service import whatsapp_service
from app.database import AsyncSessionLocal

INACTIVE_DAYS = 30
ONBOARDING_DAYS = 3
MILESTONE_TX = 10


def assign_rfm_tier(recency_days: int, frequency: int, monetary: float) -> str:
    """GOLD / SILVER / BRONZE from Recency, Frequency, Monetary."""
    if frequency >= 5 and monetary >= 250_000 and recency_days <= 30:
        return "GOLD"
    if frequency >= 2 and monetary >= 100_000 and recency_days <= 60:
        return "SILVER"
    if frequency >= 1:
        return "BRONZE"
    return "INACTIVE"


async def compute_rfm_tiers(db: AsyncSession, koperasi_ref: str) -> list[dict]:
    """
    RFM from transaksi via relasi_transaksi_pihak OR nama_pelanggan match.
    Avoids fragile NIK joins.
    """
    result = await db.execute(
        text(
            """
            WITH tx AS (
                SELECT
                    a.anggota_ref,
                    a.nama,
                    t.transaksi_sample_id,
                    t.total_pembayaran,
                    t.tanggal_dibuat
                FROM koptumbuh.anggota_koperasi a
                LEFT JOIN koptumbuh.relasi_transaksi_pihak r
                    ON r.anggota_ref = a.anggota_ref
                LEFT JOIN koptumbuh.transaksi_penjualan t
                    ON t.transaksi_sample_id = r.transaksi_sample_id
                    AND t.koperasi_ref = a.koperasi_ref
                    AND COALESCE(t.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
                WHERE a.koperasi_ref = :r

                UNION

                SELECT
                    a.anggota_ref,
                    a.nama,
                    t.transaksi_sample_id,
                    t.total_pembayaran,
                    t.tanggal_dibuat
                FROM koptumbuh.anggota_koperasi a
                JOIN koptumbuh.transaksi_penjualan t
                    ON t.koperasi_ref = a.koperasi_ref
                    AND LOWER(TRIM(t.nama_pelanggan)) = LOWER(TRIM(a.nama))
                    AND COALESCE(t.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
                WHERE a.koperasi_ref = :r
            )
            SELECT
                anggota_ref,
                MAX(nama) AS nama,
                COUNT(DISTINCT transaksi_sample_id) FILTER (WHERE transaksi_sample_id IS NOT NULL) AS frequency,
                COALESCE(SUM(total_pembayaran) FILTER (WHERE transaksi_sample_id IS NOT NULL), 0) AS monetary,
                MAX(tanggal_dibuat) AS last_tx
            FROM tx
            GROUP BY anggota_ref
            """
        ),
        {"r": koperasi_ref},
    )
    rows = []
    today = date.today()
    for r in result.fetchall():
        last_tx = r[4]
        if last_tx:
            last_d = last_tx.date() if hasattr(last_tx, "date") else last_tx
            recency = (today - last_d).days
        else:
            recency = 999
        frequency = int(r[2] or 0)
        monetary = float(r[3] or 0)
        tier = assign_rfm_tier(recency, frequency, monetary)
        rows.append({
            "anggota_ref": r[0],
            "nama": r[1],
            "recency_days": recency,
            "frequency": frequency,
            "monetary": monetary,
            "tier": tier,
            "last_tx": str(last_tx) if last_tx else None,
            "inactive": recency > INACTIVE_DAYS,
        })
    return rows


async def _resolve_whatsapp(db: AsyncSession, koperasi_ref: str, member_name: str | None) -> str | None:
    """Match WA number by pelanggan or pengguna nama — no NIK join."""
    if not member_name:
        return None
    name = member_name.strip().lower()

    pelanggan = (
        await db.execute(
            select(PelangganKoptumbuh).where(
                PelangganKoptumbuh.koperasi_ref == koperasi_ref,
                PelangganKoptumbuh.status_aktif == True,  # noqa: E712
            )
        )
    ).scalars().all()
    for p in pelanggan:
        if p.nama_pelanggan and p.nomor_whatsapp:
            pn = p.nama_pelanggan.lower()
            if name in pn or pn in name:
                return p.nomor_whatsapp

    users = (
        await db.execute(
            select(PenggunaKoptumbuh).where(
                PenggunaKoptumbuh.koperasi_ref == koperasi_ref,
                PenggunaKoptumbuh.status_aktif == True,  # noqa: E712
            )
        )
    ).scalars().all()
    for u in users:
        if u.nama and u.nomor_whatsapp:
            un = u.nama.lower()
            if name in un or un in name or any(part and part in name for part in un.split()):
                return u.nomor_whatsapp
    return None


@celery_app.task
def check_member_milestones(koperasi_ref: str = None):
    ref = koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_milestones(ref))
    finally:
        loop.close()


async def _milestones(koperasi_ref: str):
    async with AsyncSessionLocal() as db:
        rfm = await compute_rfm_tiers(db, koperasi_ref)
        celebrated = 0
        for m in rfm:
            if m["frequency"] == MILESTONE_TX:
                wa = await _resolve_whatsapp(db, koperasi_ref, m["nama"])
                if wa:
                    await whatsapp_service.send_message(
                        wa,
                        f"Selamat {m['nama']}! Ini transaksi ke-{MILESTONE_TX} Anda di koperasi. "
                        f"Tier Anda: {m['tier']}. Terima kasih atas kepercayaan Anda!",
                    )
                    celebrated += 1
        return {
            "celebrated": celebrated,
            "rfm_count": len(rfm),
            "tiers": {
                "GOLD": sum(1 for m in rfm if m["tier"] == "GOLD"),
                "SILVER": sum(1 for m in rfm if m["tier"] == "SILVER"),
                "BRONZE": sum(1 for m in rfm if m["tier"] == "BRONZE"),
                "INACTIVE": sum(1 for m in rfm if m["tier"] == "INACTIVE"),
            },
        }


@celery_app.task
def run_winback_campaign(koperasi_ref: str = None):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_winback(koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"))
    finally:
        loop.close()


async def _winback(koperasi_ref: str):
    """Winback members with RFM recency > 30 days (no NIK joins)."""
    async with AsyncSessionLocal() as db:
        rfm = await compute_rfm_tiers(db, koperasi_ref)
        inactive = [m for m in rfm if m["inactive"] and m["frequency"] >= 0]
        sent = 0
        for m in inactive[:20]:
            wa = await _resolve_whatsapp(db, koperasi_ref, m["nama"])
            if not wa:
                continue
            days = m["recency_days"] if m["recency_days"] < 999 else "lama"
            await whatsapp_service.send_message(
                wa,
                f"Halo {m['nama']}! Sudah {days} hari tidak belanja di koperasi. "
                f"Ada yang bisa kami bantu? Balas TANYA untuk info produk.",
            )
            sent += 1
        return {"sent": sent, "inactive": len(inactive)}


@celery_app.task
def send_onboarding_messages(koperasi_ref: str = None):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_onboard(koperasi_ref or "KOP-JasaAI-A1B2C3D4E5F6"))
    finally:
        loop.close()


async def _onboard(koperasi_ref: str):
    """Members registered in last 3 days without a first purchase."""
    async with AsyncSessionLocal() as db:
        cutoff = date.today() - timedelta(days=ONBOARDING_DAYS)
        members = (
            await db.execute(
                select(AnggotaKoperasi).where(
                    AnggotaKoperasi.koperasi_ref == koperasi_ref,
                    AnggotaKoperasi.tanggal_terdaftar >= cutoff,
                )
            )
        ).scalars().all()
        rfm_by_ref = {m["anggota_ref"]: m for m in await compute_rfm_tiers(db, koperasi_ref)}
        sent = 0
        for m in members:
            stats = rfm_by_ref.get(m.anggota_ref)
            if stats and stats["frequency"] > 0:
                continue
            wa = await _resolve_whatsapp(db, koperasi_ref, m.nama)
            if not wa:
                continue
            await whatsapp_service.send_message(
                wa,
                f"Selamat bergabung, {m.nama}! Gunakan WhatsApp untuk belanja: "
                f"kirim 'beli [produk] [jumlah]'. Bayar Tunai atau Simpanan.",
            )
            sent += 1
        return {"sent": sent}
