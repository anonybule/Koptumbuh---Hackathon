import json, uuid, re
from datetime import datetime
from sqlalchemy import select, or_
from app.workers.celery_app import celery_app
from app.models.koptumbuh import PesanMasuk, ParsingPesan, PenggunaKoptumbuh, ArtikelPengetahuan
from app.services.ai_service import parse_text_to_json, transcribe_audio, ocr_receipt
from app.services.whatsapp_service import whatsapp_service
from app.database import AsyncSessionLocal
from app.config import settings

RECEIPT_INTENTS = frozenset({"RECORD_RECEIPT", "RECORD_PURCHASE", "RECEIPT"})
_WORD_RE = re.compile(r"[a-zA-Z0-9\u00C0-\u024F]{3,}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_message(self, pesan_id: str):
    """Orchestrate full message pipeline: route -> extract -> validate -> dispatch."""
    import asyncio
    from celery.exceptions import MaxRetriesExceededError

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_async_process(pesan_id))
    except MaxRetriesExceededError:
        raise
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            raise
    finally:
        loop.close()


async def _async_process(pesan_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PesanMasuk).where(PesanMasuk.pesan_id == pesan_id))
        pesan = result.scalar_one_or_none()
        if not pesan:
            return
        # Skip terminal states; allow RECEIVED / FAILED / PROCESSING (retry)
        if pesan.status in ("CONFIRMED", "PARSED", "NEEDS_REVIEW", "CANCELLED"):
            return

        pesan.status = "PROCESSING"
        await db.commit()

        # Route based on input_type
        extracted = None
        try:
            if pesan.input_type == "TEXT":
                extracted = await parse_text_to_json(pesan.raw_text or "")
            elif pesan.input_type == "VOICE":
                media_bytes, mime_type = await whatsapp_service.download_media(pesan.whatsapp_message_id)
                transcript = await transcribe_audio(media_bytes, mime_type)
                if transcript:
                    pesan.raw_text = transcript
                    extracted = await parse_text_to_json(transcript)
            elif pesan.input_type == "PHOTO":
                media_bytes, mime_type = await whatsapp_service.download_media(pesan.whatsapp_message_id)
                extracted = await ocr_receipt(media_bytes, mime_type)
                # Low OCR confidence → human review, skip auto pipeline
                if extracted:
                    score = float(extracted.get("confidence_score") or 0)
                    if score < settings.MIN_PHOTO_CONFIDENCE:
                        pesan.status = "NEEDS_REVIEW"
                        await db.commit()
                        return
        except Exception:
            pesan.status = "FAILED"
            await db.commit()
            raise

        if not extracted:
            pesan.status = "FAILED"
            await db.commit()
            return

        intent = (extracted.get("intent") or "UNRESOLVED").upper().strip()
        # Normalize aliases
        if intent == "RECEIPT":
            intent = "RECORD_RECEIPT"
        extracted["intent"] = intent

        # ASK_KNOWLEDGE — ILIKE search, reply, mark done (no sale confirm)
        if intent == "ASK_KNOWLEDGE":
            await _handle_knowledge(db, pesan, extracted)
            return

        if intent == "UNRESOLVED":
            pesan.status = "NEEDS_REVIEW"
            await db.commit()
            return

        score = min(max(float(extracted.get("confidence_score", 0) or 0), 0), 1)

        if intent in RECEIPT_INTENTS:
            await _handle_receipt(db, pesan, extracted, score)
            return

        if intent == "ADJUST_STOCK":
            await _handle_adjustment(db, pesan, extracted, score)
            return

        # RECORD_SALE (default) — existing sale pipeline
        parsing = ParsingPesan(
            pesan_id=pesan.pesan_id,
            parser_version="gemini-2.5-flash-v1",
            detected_intent=intent,
            extracted_payload=extracted,
            confidence_score=score,
            status="DRAFT",
        )
        db.add(parsing)
        await db.commit()
        await db.refresh(parsing)

        from app.workers.validator import validate_parsing
        validate_parsing.delay(str(parsing.parsing_id))


async def _get_user(db, pengguna_id):
    user_result = await db.execute(
        select(PenggunaKoptumbuh).where(PenggunaKoptumbuh.pengguna_id == pengguna_id)
    )
    return user_result.scalar_one_or_none()


async def _handle_knowledge(db, pesan, extracted):
    """Search artikel_pengetahuan via ILIKE, answer via WhatsApp, mark CONFIRMED."""
    question = (
        extracted.get("question")
        or pesan.raw_text
        or ""
    ).strip()
    words = _WORD_RE.findall(question)[:6]
    articles = []
    if words:
        conditions = []
        for w in words:
            pattern = f"%{w}%"
            conditions.append(ArtikelPengetahuan.judul.ilike(pattern))
            conditions.append(ArtikelPengetahuan.isi.ilike(pattern))
        articles_result = await db.execute(
            select(ArtikelPengetahuan)
            .where(ArtikelPengetahuan.koperasi_ref == pesan.koperasi_ref)
            .where(ArtikelPengetahuan.status_aktif == True)
            .where(or_(*conditions))
            .limit(5)
        )
        articles = list(articles_result.scalars().all())

    # Fallback: any active articles if no keyword hit
    if not articles:
        articles_result = await db.execute(
            select(ArtikelPengetahuan)
            .where(ArtikelPengetahuan.koperasi_ref == pesan.koperasi_ref)
            .where(ArtikelPengetahuan.status_aktif == True)
            .limit(3)
        )
        articles = list(articles_result.scalars().all())

    from app.services.ai_service import answer_knowledge_question
    answer = await answer_knowledge_question(question, articles)

    user = await _get_user(db, pesan.pengguna_id)
    if user:
        await whatsapp_service.send_message(user.nomor_whatsapp, answer)

    pesan.status = "CONFIRMED"  # DONE equivalent in schema
    pesan.processed_at = datetime.utcnow()
    await db.commit()


async def _match_products(db, koperasi_ref: str, items: list) -> tuple[list[dict], list[str]]:
    from app.models.products import ProdukKoperasi
    from app.workers.validator import match_product

    products = await db.execute(
        select(ProdukKoperasi).where(ProdukKoperasi.koperasi_ref == koperasi_ref)
    )
    product_list = list(products.scalars().all())
    resolved: list[dict] = []
    unmatched: list[str] = []
    for item in items:
        matched = match_product(item.get("product_name", ""), product_list)
        if matched:
            resolved.append({
                "produk_sample_id": matched.produk_sample_id,
                "nama_produk": matched.nama_produk,
                "quantity": float(item.get("quantity") or 1),
                "unit": item.get("unit") or matched.unit or "pcs",
            })
        else:
            unmatched.append(item.get("product_name", "?"))
    return resolved, unmatched


async def _handle_receipt(db, pesan, extracted, score: float):
    """RECORD_RECEIPT / RECORD_PURCHASE — draft barang_masuk + notify operator."""
    from app.models.products import BarangMasukProduk

    items = extracted.get("line_items") or []
    resolved, unmatched = await _match_products(db, pesan.koperasi_ref, items)

    created_refs = []
    for item in resolved:
        bm_ref = f"BM-{uuid.uuid4().hex[:12].upper()}"
        bm = BarangMasukProduk(
            barang_masuk_ref=bm_ref,
            produk_sample_id=item["produk_sample_id"],
            koperasi_ref=pesan.koperasi_ref,
            nama_produk=item["nama_produk"],
            jumlah_masuk=item["quantity"],
            jumlah_tersedia=item["quantity"],
            status="Draft",
            keterangan=f"WhatsApp restock draft from pesan {pesan.pesan_id}",
            tanggal_masuk=datetime.utcnow(),
        )
        db.add(bm)
        created_refs.append(f"{item['nama_produk']} x{item['quantity']:.0f}")

    parsing = ParsingPesan(
        pesan_id=pesan.pesan_id,
        parser_version="gemini-2.5-flash-v1",
        detected_intent=extracted.get("intent", "RECORD_RECEIPT"),
        extracted_payload={**extracted, "resolved_items": resolved, "unmatched": unmatched},
        confidence_score=score,
        status="VALID" if resolved else "INVALID",
        validation_errors=[f"PRODUCT_NOT_FOUND: {n}" for n in unmatched],
    )
    db.add(parsing)

    user = await _get_user(db, pesan.pengguna_id)
    if user:
        if created_refs:
            lines = "\n".join(f"• {r}" for r in created_refs)
            msg = (
                "📦 *Draft Barang Masuk*\n\n"
                f"{lines}\n\n"
                "Status: Draft — tinjau di dashboard Restock untuk konfirmasi."
            )
            if unmatched:
                msg += f"\n\n⚠️ Tidak cocok: {', '.join(unmatched)}"
        else:
            msg = (
                "⚠️ *Restock tidak dapat diproses*\n"
                "Produk tidak dikenali. Kirim ulang dengan nama produk yang benar."
            )
        await whatsapp_service.send_message(user.nomor_whatsapp, msg)

    pesan.status = "PARSED" if resolved else "NEEDS_REVIEW"
    pesan.processed_at = datetime.utcnow()
    await db.commit()


async def _handle_adjustment(db, pesan, extracted, score: float):
    """ADJUST_STOCK — match products, await YA confirmation before inventaris change."""
    import redis as redis_lib

    items = extracted.get("line_items") or []
    resolved, unmatched = await _match_products(db, pesan.koperasi_ref, items)

    if not resolved:
        pesan.status = "NEEDS_REVIEW"
        await db.commit()
        user = await _get_user(db, pesan.pengguna_id)
        if user:
            await whatsapp_service.send_message(
                user.nomor_whatsapp,
                "⚠️ Penyesuaian stok gagal: produk tidak dikenali.\n"
                f"Tidak cocok: {', '.join(unmatched) or '-'}",
            )
        return

    parsing = ParsingPesan(
        pesan_id=pesan.pesan_id,
        parser_version="gemini-2.5-flash-v1",
        detected_intent="ADJUST_STOCK",
        extracted_payload={**extracted, "resolved_items": resolved, "unmatched": unmatched},
        confidence_score=score,
        status="VALID",
        validation_errors=[f"PRODUCT_NOT_FOUND: {n}" for n in unmatched],
    )
    db.add(parsing)
    await db.commit()
    await db.refresh(parsing)

    user = await _get_user(db, pesan.pengguna_id)
    if not user:
        pesan.status = "FAILED"
        await db.commit()
        return

    redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.setex(
        f"session:{user.nomor_whatsapp}",
        900,
        json.dumps({
            "state": "AWAITING_CONFIRMATION",
            "parsing_id": str(parsing.parsing_id),
            "intent": "ADJUST_STOCK",
        }),
    )

    lines = "\n".join(
        f"{i + 1}. {it['nama_produk']}  Δ {it['quantity']:+.0f} {it.get('unit', '')}"
        for i, it in enumerate(resolved)
    )
    message = (
        "📋 *Konfirmasi Penyesuaian Stok*\n\n"
        f"{lines}\n\n"
        "Balas:\n"
        "✅ *YA* — Terapkan\n"
        "✏️ *UBAH* — Koreksi & kirim ulang\n"
        "❌ *BATAL* — Batalkan"
    )
    await whatsapp_service.send_message(user.nomor_whatsapp, message)

    pesan.status = "PARSED"
    pesan.processed_at = datetime.utcnow()
    await db.commit()
