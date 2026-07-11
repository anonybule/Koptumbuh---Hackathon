"""Network Supply — multi-Kopdes stock, needs, and batch PO for regional logistics."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.api.deps import get_current_user, require_operator
from app.schemas.common import ApiResponse
from app.workers.supply_chain import compute_restock_plan, _auto_po

router = APIRouter(prefix="/admin/network-supply", tags=["admin-network-supply"])


async def _user_wilayah(db: AsyncSession, koperasi_ref: str) -> dict | None:
    row = (
        await db.execute(
            text(
                "SELECT h.kode_wilayah, w.provinsi, w.kab_kota, w.kecamatan, w.desa_kelurahan "
                "FROM koptumbuh.referensi_koperasi_wilayah h "
                "LEFT JOIN koptumbuh.referensi_wilayah w ON w.kode_wilayah=h.kode_wilayah "
                "WHERE h.koperasi_ref=:r"
            ),
            {"r": koperasi_ref},
        )
    ).fetchone()
    if not row:
        return None
    return {
        "kode_wilayah": row[0],
        "provinsi": row[1],
        "kab_kota": row[2],
        "kecamatan": row[3],
        "desa_kelurahan": row[4],
    }


def _wilayah_prefix(kode: str | None, scope: str) -> str | None:
    """Match SIMKOPDES hierarchical codes: 32.01.06.2009 → province/kab/kec prefixes."""
    if not kode:
        return None
    parts = kode.split(".")
    if scope == "provinsi":
        return parts[0] if parts else None
    if scope == "kab_kota":
        return ".".join(parts[:2]) if len(parts) >= 2 else kode
    if scope == "kecamatan":
        return ".".join(parts[:3]) if len(parts) >= 3 else kode
    return kode  # desa exact


async def _network_stores(
    db: AsyncSession,
    user: dict,
    scope: str,
    kode_wilayah: str | None = None,
) -> list[dict]:
    home = await _user_wilayah(db, user["koperasi_ref"])
    prefix = None
    if kode_wilayah:
        prefix = _wilayah_prefix(kode_wilayah, scope if scope != "desa" else "desa")
        if scope == "desa":
            prefix = kode_wilayah
    elif home and home.get("kode_wilayah"):
        prefix = _wilayah_prefix(home["kode_wilayah"], scope)
    elif user["role"] not in ("PEMBINA", "ADMIN"):
        # Fallback: only own store
        prefix = None

    params: dict = {}
    where = ["1=1"]
    if user["role"] not in ("PEMBINA", "ADMIN") and not prefix:
        where.append("p.koperasi_ref=:own")
        params["own"] = user["koperasi_ref"]
    elif prefix:
        if scope == "desa" or (kode_wilayah and scope == "desa"):
            where.append("h.kode_wilayah=:kw")
            params["kw"] = prefix
        else:
            where.append("h.kode_wilayah LIKE :pref")
            params["pref"] = f"{prefix}%"

    clause = " AND ".join(where)
    rows = (
        await db.execute(
            text(
                f"SELECT p.koperasi_ref, p.nama_koperasi, p.alamat_lengkap, h.kode_wilayah, "
                f"w.desa_kelurahan, w.kecamatan, w.kab_kota, w.provinsi "
                f"FROM koptumbuh.profil_koperasi p "
                f"LEFT JOIN koptumbuh.referensi_koperasi_wilayah h ON h.koperasi_ref=p.koperasi_ref "
                f"LEFT JOIN koptumbuh.referensi_wilayah w ON w.kode_wilayah=h.kode_wilayah "
                f"WHERE {clause} ORDER BY w.desa_kelurahan NULLS LAST, p.nama_koperasi"
            ),
            params,
        )
    ).fetchall()

    stores = []
    for r in rows:
        ref = r[0]
        low = (
            await db.execute(
                text(
                    "SELECT COUNT(*) FROM koptumbuh.inventaris_produk "
                    "WHERE koperasi_ref=:r AND stok < 5"
                ),
                {"r": ref},
            )
        ).scalar() or 0
        skus = (
            await db.execute(
                text("SELECT COUNT(*) FROM koptumbuh.inventaris_produk WHERE koperasi_ref=:r"),
                {"r": ref},
            )
        ).scalar() or 0
        draft_po = 0
        try:
            draft_po = int(
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

        stores.append(
            {
                "koperasi_ref": ref,
                "nama_koperasi": r[1],
                "alamat": r[2],
                "kode_wilayah": r[3],
                "desa": r[4],
                "kecamatan": r[5],
                "kab_kota": r[6],
                "provinsi": r[7],
                "sku_count": int(skus),
                "low_stock_count": int(low),
                "draft_po_count": draft_po,
                "is_home": ref == user.get("koperasi_ref"),
            }
        )
    return stores


@router.get("/overview", response_model=ApiResponse)
async def network_overview(
    scope: str = Query("kecamatan", pattern="^(desa|kecamatan|kab_kota|provinsi)$"),
    kode_wilayah: str | None = None,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    home = await _user_wilayah(db, user["koperasi_ref"])
    stores = await _network_stores(db, user, scope, kode_wilayah)
    return ApiResponse(
        data={
            "scope": scope,
            "home_wilayah": home,
            "store_count": len(stores),
            "stores_needing_restock": sum(1 for s in stores if s["low_stock_count"] > 0),
            "total_low_stock_skus": sum(s["low_stock_count"] for s in stores),
            "total_draft_pos": sum(s["draft_po_count"] for s in stores),
            "stores": stores,
        }
    )


@router.get("/needs", response_model=ApiResponse)
async def network_needs(
    scope: str = Query("kecamatan", pattern="^(desa|kecamatan|kab_kota|provinsi)$"),
    kode_wilayah: str | None = None,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Per-store restock plans + consolidated product needs across the network."""
    stores = await _network_stores(db, user, scope, kode_wilayah)
    by_store: list[dict] = []
    consolidated: dict[str, dict] = {}

    for s in stores:
        plan = await compute_restock_plan(db, s["koperasi_ref"])
        by_store.append(
            {
                "koperasi_ref": s["koperasi_ref"],
                "nama_koperasi": s["nama_koperasi"],
                "desa": s["desa"],
                "items": plan,
                "item_count": len(plan),
            }
        )
        for item in plan:
            key = (item.get("nama_produk") or "").strip().lower()
            if not key:
                continue
            bucket = consolidated.setdefault(
                key,
                {
                    "nama_produk": item["nama_produk"],
                    "total_suggested_qty": 0.0,
                    "stores_needing": 0,
                    "min_days_remaining": None,
                    "store_breakdown": [],
                },
            )
            bucket["total_suggested_qty"] += float(item.get("suggested_qty") or 0)
            bucket["stores_needing"] += 1
            days = item.get("days_remaining")
            if days is not None:
                if bucket["min_days_remaining"] is None or days < bucket["min_days_remaining"]:
                    bucket["min_days_remaining"] = days
            bucket["store_breakdown"].append(
                {
                    "koperasi_ref": s["koperasi_ref"],
                    "nama_koperasi": s["nama_koperasi"],
                    "desa": s["desa"],
                    "stock": item.get("stock"),
                    "ads": item.get("ads"),
                    "days_remaining": days,
                    "suggested_qty": item.get("suggested_qty"),
                }
            )

    consolidated_list = sorted(
        consolidated.values(),
        key=lambda x: (
            x["min_days_remaining"] is None,
            x["min_days_remaining"] if x["min_days_remaining"] is not None else 0,
            -x["stores_needing"],
        ),
    )
    for c in consolidated_list:
        c["total_suggested_qty"] = round(c["total_suggested_qty"], 3)

    return ApiResponse(
        data={
            "scope": scope,
            "by_store": by_store,
            "consolidated": consolidated_list,
            "stores_with_needs": sum(1 for b in by_store if b["item_count"] > 0),
        }
    )


@router.get("/matrix", response_model=ApiResponse)
async def network_matrix(
    scope: str = Query("kecamatan", pattern="^(desa|kecamatan|kab_kota|provinsi)$"),
    kode_wilayah: str | None = None,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Product × store stock matrix (normalized by product name)."""
    stores = await _network_stores(db, user, scope, kode_wilayah)
    if not stores:
        return ApiResponse(data={"products": [], "stores": [], "cells": []})

    refs = [s["koperasi_ref"] for s in stores]
    # Build dynamic IN clause
    placeholders = ", ".join(f":r{i}" for i in range(len(refs)))
    params = {f"r{i}": refs[i] for i in range(len(refs))}

    rows = (
        await db.execute(
            text(
                f"SELECT i.koperasi_ref, i.nama_produk, i.stok, i.produk_sample_id "
                f"FROM koptumbuh.inventaris_produk i "
                f"WHERE i.koperasi_ref IN ({placeholders}) "
                f"ORDER BY i.nama_produk, i.koperasi_ref"
            ),
            params,
        )
    ).fetchall()

    # Also flag needs from restock plans
    need_keys: set[tuple[str, str]] = set()
    for s in stores:
        plan = await compute_restock_plan(db, s["koperasi_ref"])
        for item in plan:
            need_keys.add((s["koperasi_ref"], (item.get("nama_produk") or "").strip().lower()))

    products_map: dict[str, str] = {}
    cells = []
    for r in rows:
        name = r[1] or ""
        key = name.strip().lower()
        products_map[key] = name
        cells.append(
            {
                "koperasi_ref": r[0],
                "nama_produk": name,
                "product_key": key,
                "stock": float(r[2] or 0),
                "produk_sample_id": r[3],
                "needs_restock": (r[0], key) in need_keys,
                "critical": float(r[2] or 0) < 5,
            }
        )

    products = [{"key": k, "nama_produk": v} for k, v in sorted(products_map.items(), key=lambda x: x[1])]
    return ApiResponse(
        data={
            "scope": scope,
            "stores": [
                {
                    "koperasi_ref": s["koperasi_ref"],
                    "nama_koperasi": s["nama_koperasi"],
                    "desa": s["desa"],
                    "short_name": (s["desa"] or s["nama_koperasi"] or "")[:18],
                }
                for s in stores
            ],
            "products": products,
            "cells": cells,
        }
    )


class BatchPoBody(BaseModel):
    scope: str = Field("kecamatan", pattern="^(desa|kecamatan|kab_kota|provinsi)$")
    kode_wilayah: str | None = None
    koperasi_refs: list[str] | None = None
    only_with_needs: bool = True


@router.post("/batch-po", response_model=ApiResponse)
async def network_batch_po(
    body: BatchPoBody,
    user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """Generate DRAFT purchase orders for multiple Kopdes in the selected wilayah range."""
    stores = await _network_stores(db, user, body.scope, body.kode_wilayah)
    allowed = {s["koperasi_ref"] for s in stores}
    targets = body.koperasi_refs or list(allowed)
    targets = [t for t in targets if t in allowed]
    if not targets:
        raise HTTPException(status_code=400, detail="No cooperatives in range / selection")

    results = []
    for ref in targets:
        plan = await compute_restock_plan(db, ref)
        if body.only_with_needs and not plan:
            results.append({"koperasi_ref": ref, "created": 0, "skipped": True, "reason": "no_needs"})
            continue
        try:
            out = await _auto_po(ref)
            results.append({"koperasi_ref": ref, "skipped": False, **(out or {})})
        except Exception as e:
            await db.rollback()
            results.append({"koperasi_ref": ref, "created": 0, "error": str(e)})

    created = sum(int(r.get("created") or 0) for r in results)
    return ApiResponse(
        data={
            "scope": body.scope,
            "targets": len(targets),
            "pos_created": created,
            "results": results,
        }
    )
