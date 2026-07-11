import re
from datetime import datetime
from sqlalchemy import select
from app.workers.celery_app import celery_app
from app.models.koptumbuh import ParsingPesan, PesanMasuk
from app.models.products import ProdukKoperasi, BarangMasukProduk, InventarisProduk
from app.models.members import AnggotaKoperasi
from app.services.normalize import normalize_unit, normalize_payment
from app.database import AsyncSessionLocal
import redis as redis_lib
from app.config import settings

redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def _tokens(name: str) -> set[str]:
    return set(_TOKEN_RE.findall((name or "").lower()))


def token_jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def match_product(product_name: str, product_list: list) -> ProdukKoperasi | None:
    """Exact → substring/ILIKE → token Jaccard ≥ 0.5."""
    needle = (product_name or "").lower().strip()
    if not needle:
        return None

    by_exact = {p.nama_produk.lower().strip(): p for p in product_list if p.nama_produk}
    if needle in by_exact:
        return by_exact[needle]

    for name, prod in by_exact.items():
        if needle in name or name in needle:
            return prod

    best, best_score = None, 0.0
    for prod in product_list:
        score = token_jaccard(needle, prod.nama_produk or "")
        if score >= 0.5 and score > best_score:
            best, best_score = prod, score
    return best


@celery_app.task(bind=True, max_retries=2)
def validate_parsing(self, parsing_id: str):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_async_validate(parsing_id))
    finally:
        loop.close()


async def _async_validate(parsing_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ParsingPesan).where(ParsingPesan.parsing_id == parsing_id))
        parsing = result.scalar_one_or_none()
        if not parsing or parsing.status != "DRAFT":
            return

        payload = parsing.extracted_payload or {}
        errors = []
        resolved_items = []

        pesan_result = await db.execute(select(PesanMasuk).where(PesanMasuk.pesan_id == parsing.pesan_id))
        pesan = pesan_result.scalar_one_or_none()
        if not pesan:
            return
        koperasi_ref = pesan.koperasi_ref

        products_result = await db.execute(
            select(ProdukKoperasi).where(ProdukKoperasi.koperasi_ref == koperasi_ref)
        )
        product_list = list(products_result.scalars().all())

        members_result = await db.execute(
            select(AnggotaKoperasi).where(AnggotaKoperasi.koperasi_ref == koperasi_ref)
        )
        member_list = members_result.scalars().all()

        inv_result = await db.execute(
            select(InventarisProduk).where(InventarisProduk.koperasi_ref == koperasi_ref)
        )
        inventory = {i.produk_sample_id: i for i in inv_result.scalars().all()}

        for item in payload.get("line_items", []):
            matched = match_product(item.get("product_name", ""), product_list)
            if not matched:
                errors.append(f"PRODUCT_NOT_FOUND: {item.get('product_name')}")
                continue

            price_result = await db.execute(
                select(BarangMasukProduk.harga_jual)
                .where(BarangMasukProduk.produk_sample_id == matched.produk_sample_id)
                .where(BarangMasukProduk.koperasi_ref == koperasi_ref)
                .order_by(BarangMasukProduk.tanggal_masuk.desc())
                .limit(1)
            )
            price_row = price_result.scalar_one_or_none()
            db_price = float(price_row) if price_row and float(price_row) > 0 else 0

            if db_price == 0:
                errors.append(f"NO_PRICE: {item.get('product_name')}")
                continue

            qty = float(item.get("quantity", 1) or 1)
            unit = normalize_unit(item.get("unit") or matched.unit)

            inv = inventory.get(matched.produk_sample_id)
            stok = float(inv.stok or 0) if inv else 0.0
            if stok < qty:
                errors.append(
                    f"STOCK_INSUFFICIENT: {matched.nama_produk} stok={stok:.0f} butuh={qty:.0f}"
                )
                continue

            resolved_items.append({
                "produk_sample_id": matched.produk_sample_id,
                "nama_produk": matched.nama_produk,
                "quantity": qty,
                "unit": unit,
                "unit_price": db_price,
                "subtotal": round(qty * db_price, 2),
            })

        customer_name = payload.get("customer_name", "").lower().strip()
        customer_ref = None
        if customer_name:
            for m in member_list:
                if m.nama and (customer_name in m.nama.lower() or m.nama.lower() in customer_name):
                    customer_ref = m.anggota_ref
                    break

        calculated_total = sum(ri["subtotal"] for ri in resolved_items)

        if not payload.get("line_items") or len(payload["line_items"]) == 0:
            errors.append("EMPTY_TRANSACTION: No items detected")
        if not resolved_items:
            errors.append("NO_VALID_ITEMS: Could not match any products")

        parsing.extracted_payload = {
            **payload,
            "resolved_items": resolved_items,
            "calculated_total": calculated_total,
            "customer_ref": customer_ref,
            "payment_method": normalize_payment(payload.get("payment_method")),
        }
        parsing.validation_errors = errors
        # Never VALID with empty resolved_items; STOCK_INSUFFICIENT → INVALID
        parsing.status = "VALID" if (not errors and resolved_items) else "INVALID"
        await db.commit()

        pesan.status = "PARSED" if parsing.status == "VALID" else "NEEDS_REVIEW"
        pesan.processed_at = datetime.utcnow()
        await db.commit()

        from app.workers.dispatcher import dispatch_confirmation
        dispatch_confirmation.delay(str(parsing.parsing_id))
