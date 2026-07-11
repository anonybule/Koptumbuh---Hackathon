"""SHU (Sisa Hasil Usaha) estimation engine.

Formula (demo-realistic, from daily ops data):
  Pendapatan  = SUM(transaksi_penjualan.total_pembayaran) YTD
  HPP         = SUM(qty_keluar × harga_beli terakhir) YTD
  Laba kotor  = Pendapatan − HPP
  Beban ops   = max(estimated opex, 8% of pendapatan) when no ledger
  SHU kotor   = Laba kotor − Beban
  SHU bersih  = SHU kotor × (1 − pajak_rate)

Member allocation (typical koperasi split of distributable SHU):
  40% jasa anggota (by belanja)
  30% jasa modal   (by simpanan PAID)
  20% dana cadangan (retained — not paid out)
  10% dana sosial/pengurus (pool)
"""

from __future__ import annotations

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# Allocation weights of SHU bersih
WEIGHT_JASA_ANGGOTA = 0.40
WEIGHT_JASA_MODAL = 0.30
WEIGHT_CADANGAN = 0.20
WEIGHT_SOSIAL = 0.10
OPEX_RATIO = 0.08
TAX_RATIO = 0.02
MEMBER_FALLBACK_RATE = 0.05  # if coop SHU unknown: belanja × 5%


async def compute_shu_summary(db: AsyncSession, koperasi_ref: str, year: int | None = None) -> dict:
    year = year or date.today().year
    params = {"r": koperasi_ref, "y": year}

    revenue_row = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(total_pembayaran),0), COUNT(*) "
                "FROM koptumbuh.transaksi_penjualan "
                "WHERE koperasi_ref=:r "
                "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
                "AND EXTRACT(YEAR FROM COALESCE(tanggal_dibuat, dibuat_pada)) = :y"
            ),
            params,
        )
    ).fetchone()
    pendapatan = float(revenue_row[0] or 0)
    jumlah_transaksi = int(revenue_row[1] or 0)

    # HPP from outbound × latest buy price
    try:
        hpp = float(
            (
                await db.execute(
                    text(
                        "SELECT COALESCE(SUM(bk.jumlah_keluar * COALESCE(bp.harga_beli, 0)), 0) "
                        "FROM koptumbuh.barang_keluar_produk bk "
                        "LEFT JOIN LATERAL ("
                        "  SELECT harga_beli FROM koptumbuh.barang_masuk_produk bm "
                        "  WHERE bm.produk_sample_id=bk.produk_sample_id AND bm.koperasi_ref=bk.koperasi_ref "
                        "  ORDER BY bm.tanggal_masuk DESC NULLS LAST LIMIT 1"
                        ") bp ON TRUE "
                        "WHERE bk.koperasi_ref=:r "
                        "AND COALESCE(bk.status_transaksi,'') NOT IN ('Refund','Cancelled') "
                        "AND EXTRACT(YEAR FROM COALESCE(bk.tanggal_keluar, bk.dibuat_pada)) = :y"
                    ),
                    params,
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()
        # Fallback: 70% of revenue as HPP
        hpp = round(pendapatan * 0.70, 2)

    laba_kotor = pendapatan - hpp
    beban = round(pendapatan * OPEX_RATIO, 2)
    shu_kotor = laba_kotor - beban
    pajak = max(0.0, round(shu_kotor * TAX_RATIO, 2)) if shu_kotor > 0 else 0.0
    shu_bersih = shu_kotor - pajak

    margin_kotor = (laba_kotor / pendapatan * 100) if pendapatan else 0.0
    margin_shu = (shu_bersih / pendapatan * 100) if pendapatan else 0.0

    distributable = max(0.0, shu_bersih)
    pools = {
        "jasa_anggota": round(distributable * WEIGHT_JASA_ANGGOTA, 2),
        "jasa_modal": round(distributable * WEIGHT_JASA_MODAL, 2),
        "dana_cadangan": round(distributable * WEIGHT_CADANGAN, 2),
        "dana_sosial": round(distributable * WEIGHT_SOSIAL, 2),
    }

    return {
        "koperasi_ref": koperasi_ref,
        "tahun": year,
        "pendapatan": round(pendapatan, 2),
        "hpp": round(hpp, 2),
        "laba_kotor": round(laba_kotor, 2),
        "beban_operasional": beban,
        "shu_kotor": round(shu_kotor, 2),
        "pajak_estimasi": pajak,
        "shu_bersih": round(shu_bersih, 2),
        "margin_kotor_pct": round(margin_kotor, 1),
        "margin_shu_pct": round(margin_shu, 1),
        "jumlah_transaksi": jumlah_transaksi,
        "hasil": "PROFIT" if shu_bersih > 0 else ("BREAK_EVEN" if shu_bersih == 0 else "LOSS"),
        "pools": pools,
        "formula": {
            "pendapatan": "SUM(total_pembayaran) YTD",
            "hpp": "SUM(qty_keluar × harga_beli terakhir)",
            "beban": f"{int(OPEX_RATIO*100)}% pendapatan (estimasi opex)",
            "pajak": f"{int(TAX_RATIO*100)}% SHU kotor bila positif",
            "alokasi": "40% jasa anggota · 30% jasa modal · 20% cadangan · 10% sosial",
        },
    }


async def compute_shu_monthly(db: AsyncSession, koperasi_ref: str, year: int | None = None) -> list[dict]:
    year = year or date.today().year
    params = {"r": koperasi_ref, "y": year}

    rev_rows = (
        await db.execute(
            text(
                "SELECT DATE_TRUNC('month', COALESCE(tanggal_dibuat, dibuat_pada))::date AS bulan, "
                "SUM(COALESCE(total_pembayaran,0)), COUNT(*) "
                "FROM koptumbuh.transaksi_penjualan "
                "WHERE koperasi_ref=:r "
                "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
                "AND EXTRACT(YEAR FROM COALESCE(tanggal_dibuat, dibuat_pada)) = :y "
                "GROUP BY 1 ORDER BY 1 DESC"
            ),
            params,
        )
    ).fetchall()

    try:
        hpp_rows = (
            await db.execute(
                text(
                    "SELECT DATE_TRUNC('month', COALESCE(bk.tanggal_keluar, bk.dibuat_pada))::date AS bulan, "
                    "COALESCE(SUM(bk.jumlah_keluar * COALESCE(bp.harga_beli, 0)), 0) "
                    "FROM koptumbuh.barang_keluar_produk bk "
                    "LEFT JOIN LATERAL ("
                    "  SELECT harga_beli FROM koptumbuh.barang_masuk_produk bm "
                    "  WHERE bm.produk_sample_id=bk.produk_sample_id AND bm.koperasi_ref=bk.koperasi_ref "
                    "  ORDER BY bm.tanggal_masuk DESC NULLS LAST LIMIT 1"
                    ") bp ON TRUE "
                    "WHERE bk.koperasi_ref=:r "
                    "AND COALESCE(bk.status_transaksi,'') NOT IN ('Refund','Cancelled') "
                    "AND EXTRACT(YEAR FROM COALESCE(bk.tanggal_keluar, bk.dibuat_pada)) = :y "
                    "GROUP BY 1"
                ),
                params,
            )
        ).fetchall()
        hpp_map = {str(r[0]): float(r[1] or 0) for r in hpp_rows}
    except Exception:
        await db.rollback()
        hpp_map = {}

    out = []
    for r in rev_rows:
        bulan = str(r[0]) if r[0] else None
        omzet = float(r[1] or 0)
        tx = int(r[2] or 0)
        hpp = hpp_map.get(bulan, round(omzet * 0.70, 2))
        beban = round(omzet * OPEX_RATIO, 2)
        shu = omzet - hpp - beban
        if shu > 0:
            shu = round(shu * (1 - TAX_RATIO), 2)
        out.append(
            {
                "bulan": bulan,
                "total_omzet": omzet,
                "jumlah_transaksi": tx,
                "hpp": round(hpp, 2),
                "beban_operasional": beban,
                "estimasi_shu": round(shu, 2),
            }
        )
    return out


async def compute_member_shu(
    db: AsyncSession,
    koperasi_ref: str,
    year: int | None = None,
    summary: dict | None = None,
) -> list[dict]:
    year = year or date.today().year
    summary = summary or await compute_shu_summary(db, koperasi_ref, year)
    pools = summary.get("pools") or {}
    pool_anggota = float(pools.get("jasa_anggota") or 0)
    pool_modal = float(pools.get("jasa_modal") or 0)

    # Member spending via relasi or name match
    spend_rows = (
        await db.execute(
            text(
                """
                WITH spend AS (
                  SELECT a.anggota_ref, a.nama,
                    COALESCE(SUM(t.total_pembayaran), 0) AS belanja
                  FROM koptumbuh.anggota_koperasi a
                  LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref=a.anggota_ref
                  LEFT JOIN koptumbuh.transaksi_penjualan t
                    ON t.transaksi_sample_id=r.transaksi_sample_id
                    AND t.koperasi_ref=a.koperasi_ref
                    AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')
                    AND EXTRACT(YEAR FROM COALESCE(t.tanggal_dibuat, t.dibuat_pada)) = :y
                  WHERE a.koperasi_ref=:r
                  GROUP BY a.anggota_ref, a.nama
                )
                SELECT anggota_ref, nama, belanja FROM spend ORDER BY belanja DESC
                """
            ),
            {"r": koperasi_ref, "y": year},
        )
    ).fetchall()

    try:
        sav_rows = (
            await db.execute(
                text(
                    "SELECT anggota_ref, COALESCE(SUM(jumlah_simpanan),0) "
                    "FROM koptumbuh.simpanan_anggota "
                    "WHERE koperasi_ref=:r AND UPPER(COALESCE(status,'')) IN ('PAID','LUNAS','DIBAYAR') "
                    "AND EXTRACT(YEAR FROM COALESCE(dibayar_pada, dibuat_pada, NOW())) = :y "
                    "GROUP BY anggota_ref"
                ),
                {"r": koperasi_ref, "y": year},
            )
        ).fetchall()
        sav_map = {r[0]: float(r[1] or 0) for r in sav_rows}
    except Exception:
        await db.rollback()
        sav_map = {}

    total_belanja = sum(float(r[2] or 0) for r in spend_rows) or 0.0
    total_simpanan = sum(sav_map.values()) or 0.0

    members = []
    for r in spend_rows:
        ref, nama, belanja = r[0], r[1], float(r[2] or 0)
        simpanan = sav_map.get(ref, 0.0)
        jasa_trx = (belanja / total_belanja * pool_anggota) if total_belanja > 0 else 0.0
        jasa_modal = (simpanan / total_simpanan * pool_modal) if total_simpanan > 0 else 0.0
        # Fallback if SHU pools empty but member has spend
        if pool_anggota <= 0 and pool_modal <= 0 and belanja > 0:
            estimasi = round(belanja * MEMBER_FALLBACK_RATE, 2)
            jasa_trx = estimasi
            jasa_modal = 0.0
        else:
            estimasi = round(jasa_trx + jasa_modal, 2)

        members.append(
            {
                "anggota_ref": ref,
                "nama": nama,
                "belanja_ytd": round(belanja, 2),
                "simpanan_ytd": round(simpanan, 2),
                "jasa_anggota": round(jasa_trx, 2),
                "jasa_modal": round(jasa_modal, 2),
                "estimasi_shu": estimasi,
                "share_belanja_pct": round(belanja / total_belanja * 100, 1) if total_belanja else 0.0,
            }
        )

    members.sort(key=lambda m: m["estimasi_shu"], reverse=True)
    return members
