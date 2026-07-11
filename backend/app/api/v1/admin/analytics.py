"""Admin BI / Analytics APIs — insights briefing + payment mix."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.api.deps import get_current_user
from app.schemas.common import ApiResponse
from app.services.ai_service import generate_bi_insights
from app.services.shu_service import compute_shu_summary

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


async def _gather_metrics(db: AsyncSession, koperasi_ref: str) -> dict:
    params = {"r": koperasi_ref}

    sales = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(total_pembayaran),0), COUNT(*) "
                "FROM koptumbuh.transaksi_penjualan "
                "WHERE koperasi_ref=:r AND DATE(COALESCE(tanggal_dibuat, dibuat_pada))=CURRENT_DATE "
                "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')"
            ),
            params,
        )
    ).fetchone()

    low_stock = int(
        (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.inventaris_produk "
                    "WHERE koperasi_ref=:r AND stok < 5"
                ),
                params,
            )
        ).scalar()
        or 0
    )

    unpaid = int(
        (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.transaksi_penjualan "
                    "WHERE koperasi_ref=:r AND status_transaksi='Unpaid'"
                ),
                params,
            )
        ).scalar()
        or 0
    )

    try:
        slow_rows = (
            await db.execute(
                text(
                    "SELECT nama_produk, hari_tanpa_penjualan, stok_saat_ini "
                    "FROM koptumbuh.v_produk_lambat_bergerak WHERE koperasi_ref=:r "
                    "ORDER BY hari_tanpa_penjualan DESC LIMIT 5"
                ),
                params,
            )
        ).fetchall()
        slow = [
            {"produk": r[0], "hari_idle": int(r[1] or 0), "stok": float(r[2] or 0)}
            for r in slow_rows
        ]
    except Exception:
        await db.rollback()
        slow = []

    try:
        margin_rows = (
            await db.execute(
                text(
                    "SELECT nama_produk, margin_persen, total_profit "
                    "FROM koptumbuh.v_margin_produk WHERE koperasi_ref=:r "
                    "ORDER BY total_profit DESC NULLS LAST LIMIT 3"
                ),
                params,
            )
        ).fetchall()
        top_margin = [
            {"produk": r[0], "margin_pct": float(r[1] or 0), "profit": float(r[2] or 0)}
            for r in margin_rows
        ]
    except Exception:
        await db.rollback()
        top_margin = []

    try:
        at_risk = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM koptumbuh.v_segmentasi_anggota "
                        "WHERE koperasi_ref=:r AND status_retensi IN ('RISIKO_HILANG','HILANG')"
                    ),
                    params,
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()
        at_risk = 0

    mismatch = 0
    try:
        mismatch = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM koptumbuh.v_rekonsiliasi_stok "
                        "WHERE koperasi_ref=:r AND status_rekonsiliasi='MISMATCH'"
                    ),
                    params,
                )
            ).scalar()
            or 0
        )
    except Exception:
        await db.rollback()

    shu = await compute_shu_summary(db, koperasi_ref)

    return {
        "omzet_hari_ini": float(sales[0] or 0),
        "tx_hari_ini": int(sales[1] or 0),
        "stok_menipis": low_stock,
        "piutang_unpaid": unpaid,
        "anggota_risiko": at_risk,
        "stok_mismatch": mismatch,
        "slow_moving": slow,
        "top_margin": top_margin,
        "shu_bersih_ytd": shu.get("shu_bersih", 0),
        "shu_hasil": shu.get("hasil"),
        "margin_shu_pct": shu.get("margin_shu_pct"),
    }


def _fallback_insights(metrics: dict) -> dict:
    actions = []
    if metrics.get("stok_menipis", 0) > 0:
        actions.append(
            {
                "priority": "HIGH",
                "title": f"Restock {metrics['stok_menipis']} produk menipis",
                "detail": "Stok di bawah 5 unit — buka Supply atau buat draft PO.",
                "href": "/supply",
            }
        )
    if metrics.get("anggota_risiko", 0) > 0:
        actions.append(
            {
                "priority": "MED",
                "title": f"{metrics['anggota_risiko']} anggota berisiko hilang",
                "detail": "Jalankan kampanye win-back dari Customer Relationship.",
                "href": "/customer-relationship",
            }
        )
    if metrics.get("piutang_unpaid", 0) > 0:
        actions.append(
            {
                "priority": "MED",
                "title": f"{metrics['piutang_unpaid']} piutang belum lunas",
                "detail": "Tinjau transaksi Unpaid / Hutang.",
                "href": "/transactions",
            }
        )
    if metrics.get("stok_mismatch", 0) > 0:
        actions.append(
            {
                "priority": "LOW",
                "title": f"{metrics['stok_mismatch']} selisih stok",
                "detail": "Lakukan opname / penyesuaian inventaris.",
                "href": "/inventory",
            }
        )
    if not actions:
        actions.append(
            {
                "priority": "LOW",
                "title": "Dorong produk margin tinggi",
                "detail": "Lihat tab Margin dan rekomendasi bundling.",
                "href": "/recommendations",
            }
        )

    risks = []
    if metrics.get("shu_hasil") == "LOSS":
        risks.append("Estimasi SHU YTD masih rugi — cek HPP dan beban di halaman SHU.")
    for s in (metrics.get("slow_moving") or [])[:2]:
        risks.append(f"{s['produk']} idle {s['hari_idle']} hari (stok {s['stok']})")

    return {
        "headline": f"Omzet hari ini {metrics.get('tx_hari_ini', 0)} transaksi",
        "summary": (
            f"Omzet Rp {metrics.get('omzet_hari_ini', 0):,.0f} · "
            f"stok menipis {metrics.get('stok_menipis', 0)} · "
            f"SHU YTD {metrics.get('shu_hasil', '—')} "
            f"(Rp {metrics.get('shu_bersih_ytd', 0):,.0f})."
        ),
        "actions": actions[:3],
        "risks": risks[:4],
        "source": "rules",
    }


@router.get("/insights", response_model=ApiResponse)
async def analytics_insights(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    metrics = await _gather_metrics(db, user["koperasi_ref"])
    ai = await generate_bi_insights(metrics)
    if ai:
        insight = {**ai, "source": "gemini"}
    else:
        insight = _fallback_insights(metrics)
    return ApiResponse(data={"metrics": metrics, "insight": insight})


@router.get("/payment-mix", response_model=ApiResponse)
async def payment_mix(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            text(
                "SELECT COALESCE(metode_pembayaran,'Lainnya') AS metode, "
                "COUNT(*) AS jumlah, COALESCE(SUM(total_pembayaran),0) AS total "
                "FROM koptumbuh.transaksi_penjualan "
                "WHERE koperasi_ref=:r "
                "AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled') "
                "GROUP BY 1 ORDER BY total DESC"
            ),
            {"r": user["koperasi_ref"]},
        )
    ).fetchall()
    return ApiResponse(
        data=[
            {"metode": r[0], "jumlah": int(r[1] or 0), "total": float(r[2] or 0)}
            for r in rows
        ]
    )
