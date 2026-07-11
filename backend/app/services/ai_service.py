import json
from google import genai
from google.genai import types
from app.config import settings

_client = None

def _get_client():
    global _client
    if _client is None and settings.GEMINI_API_KEY:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

# Shared schema for structured extraction
EXTRACTION_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "intent": types.Schema(
            type=types.Type.STRING,
            enum=[
                "RECORD_SALE",
                "RECORD_RECEIPT",
                "RECORD_PURCHASE",
                "ADJUST_STOCK",
                "ASK_KNOWLEDGE",
                "UNRESOLVED",
            ],
        ),
        "customer_name": types.Schema(type=types.Type.STRING),
        "payment_method": types.Schema(
            type=types.Type.STRING, enum=["Cash", "Transfer", "Hutang", "Lainnya"]
        ),
        "due_date": types.Schema(type=types.Type.STRING),
        "line_items": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_name": types.Schema(type=types.Type.STRING),
                    "quantity": types.Schema(type=types.Type.NUMBER),
                    "unit": types.Schema(type=types.Type.STRING),
                },
                required=["product_name", "quantity", "unit"],
            ),
        ),
        "confidence_score": types.Schema(type=types.Type.NUMBER),
        "question": types.Schema(type=types.Type.STRING),
    },
    required=["intent", "customer_name", "line_items", "confidence_score"],
)

EXTRACTION_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=1000,
    response_mime_type="application/json",
    response_schema=EXTRACTION_SCHEMA,
    system_instruction=(
        "Anda adalah parser pesan koperasi Indonesia. Tentukan intent lalu ekstrak entitas.\n"
        "intent:\n"
        "- RECORD_SALE: penjualan / beli / bayar (kasir mencatat penjualan)\n"
        "- RECORD_RECEIPT atau RECORD_PURCHASE: barang masuk / restock / belanja stok / penerimaan barang\n"
        "- ADJUST_STOCK: penyesuaian stok / koreksi inventaris / stok hilang / opname\n"
        "- ASK_KNOWLEDGE: pertanyaan informasi (cara, syarat, SHU, simpanan, pinjaman, dll)\n"
        "- UNRESOLVED: tidak jelas\n"
        "Ekstrak produk, jumlah, nama pelanggan, metode pembayaran bila relevan. "
        "Untuk ASK_KNOWLEDGE isi field question. "
        "JANGAN menghitung total — hanya ekstrak apa yang disebutkan secara eksplisit. "
        "Jika pelanggan bayar nanti/hutang, gunakan payment_method='Hutang' dan extract due_date. "
        "Bahasa Indonesia."
    ),
)


async def parse_text_to_json(text: str) -> dict:
    """Gemini 2.5 Flash — structured extraction from text."""
    if not settings.GEMINI_API_KEY:
        return {"intent": "UNRESOLVED", "customer_name": "", "line_items": [], "confidence_score": 0}

    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=text,
            config=EXTRACTION_CONFIG,
        )
        return json.loads(response.text)
    except Exception:
        return {"intent": "UNRESOLVED", "customer_name": "", "line_items": [], "confidence_score": 0}


async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """Gemini 2.5 Flash — native audio transcription."""
    if not settings.GEMINI_API_KEY:
        return ""

    try:
        config = types.GenerateContentConfig(
            temperature=0.0,
            system_instruction="Transkripsikan audio ini ke teks Bahasa Indonesia. Jangan tambahkan apapun selain hasil transkripsi.",
        )
        part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[part],
            config=config,
        )
        return response.text
    except Exception:
        return ""


async def ocr_receipt(image_bytes: bytes, mime_type: str) -> dict:
    """Gemini 2.5 Flash — multimodal: image to structured JSON."""
    if not settings.GEMINI_API_KEY:
        return {"intent": "UNRESOLVED", "customer_name": "", "line_items": [], "confidence_score": 0}

    image_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2500,
        response_mime_type="application/json",
        response_schema=EXTRACTION_SCHEMA,
        system_instruction=(
            "Ekstrak SEMUA baris produk dari foto ini — struk, nota, ATAU daftar tulisan tangan di buku/notebook. "
            "Setiap baris terpisah = satu line_item (product_name, quantity, unit). "
            "Contoh notebook: 'Beras 5kg x2', 'Minyak 2L 3 botol', 'Gula 1kg' → beberapa line_items. "
            "intent: RECORD_RECEIPT (barang masuk/struk beli) atau RECORD_SALE (daftar penjualan). "
            "JANGAN menghitung total harga — harga dari DB (No AI Math). "
            "Jika unit tidak jelas, gunakan 'pcs'. Bahasa Indonesia. "
            "Set confidence_score rendah (<0.7) jika buram, coretan tidak terbaca, atau hanya sebagian baris jelas."
        ),
    )
    try:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                part,
                "Ekstrak SEMUA baris item (termasuk daftar notebook multi-baris). Jangan gabungkan baris.",
            ],
            config=image_config,
        )
        return json.loads(response.text)
    except Exception:
        return {"intent": "UNRESOLVED", "customer_name": "", "line_items": [], "confidence_score": 0}


async def answer_knowledge_question(question: str, articles: list) -> str:
    """Answer member questions from knowledge base articles."""
    if not articles or not settings.GEMINI_API_KEY:
        return "Maaf, saya tidak menemukan informasi tentang pertanyaan Anda. Silakan hubungi pengurus koperasi."

    qa_config = types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=500,
        system_instruction=(
            "Anda adalah asisten Koperasi Merah Putih. Jawab pertanyaan anggota "
            "berdasarkan artikel pengetahuan yang diberikan. Jika jawaban tidak "
            "ada di artikel, katakan: 'Maaf, saya tidak menemukan informasi tentang "
            "itu.' JANGAN mengarang jawaban. Gunakan Bahasa Indonesia yang ramah."
        ),
    )
    context = "\n\n".join([f"ARTIKEL: {a.judul}\n{a.isi}" for a in articles])
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[f"Pertanyaan: {question}\n\nArtikel:\n{context}"],
            config=qa_config,
        )
        return response.text
    except Exception:
        return "Maaf, terjadi kesalahan. Silakan coba lagi atau hubungi pengurus koperasi."


BI_INSIGHT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "headline": types.Schema(type=types.Type.STRING),
        "summary": types.Schema(type=types.Type.STRING),
        "actions": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "priority": types.Schema(type=types.Type.STRING, enum=["HIGH", "MED", "LOW"]),
                    "title": types.Schema(type=types.Type.STRING),
                    "detail": types.Schema(type=types.Type.STRING),
                    "href": types.Schema(type=types.Type.STRING),
                },
                required=["priority", "title", "detail", "href"],
            ),
        ),
        "risks": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["headline", "summary", "actions", "risks"],
)


async def generate_bi_insights(metrics: dict) -> dict | None:
    """Gemini briefing from structured BI metrics. Returns None if Gemini unavailable."""
    if not settings.GEMINI_API_KEY:
        return None

    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=800,
        response_mime_type="application/json",
        response_schema=BI_INSIGHT_SCHEMA,
        system_instruction=(
            "Anda adalah analis BI untuk koperasi desa Indonesia (Kopdes). "
            "Berdasarkan metrik JSON, buat ringkasan operasional singkat dalam Bahasa Indonesia. "
            "Maksimal 3 aksi konkret. href harus salah satu: "
            "/supply, /inventory, /customer-relationship, /shu, /transactions, /recommendations, /automations, /network-supply. "
            "Jangan mengarang angka di luar metrik. Fokus pada aksi yang bisa dilakukan hari ini."
        ),
    )
    try:
        response = _get_client().models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[f"Metrik koperasi hari ini:\n{json.dumps(metrics, ensure_ascii=False, default=str)}"],
            config=config,
        )
        return json.loads(response.text)
    except Exception:
        return None
