# KopTumbuh

## Product Name

**KopTumbuh** — *Koperasi Tumbuh* (Growing Cooperatives).

A WhatsApp-first, AI-powered operational platform that upgrades Indonesia’s SIMKOPDES cooperative management system with conversational transaction recording and supply chain intelligence.

**Team:** JasaAI · **Coop ref:** `KOP-JasaAI-A1B2C3D4E5F6` · **Table prefix:** `JasaAI_`

---

## Problem

Indonesia has over 127,000 active cooperatives (*koperasi*). The government mandates operational reporting through **SIMKOPDES**, a system that typically requires manual data entry by trained operators.

**The gap:**

- Many rural cooperatives still record daily sales on **paper notebooks**, then transcribe into SIMKOPDES days or weeks later
- Transcription errors, lost notebooks, and delayed reporting are common
- Operators spend hours on admin instead of serving members
- Restock and assortment decisions are intuition-driven, not data-driven
- Existing mobile/desktop tools lack a **conversational** interface operators already use every day

**KopTumbuh solves this by letting operators record transactions the way they already communicate — by sending a WhatsApp message.**

---

## Target User

| Persona | Role | Pain Point |
|---------|------|------------|
| **Budi Santoso** | Operator Kasir | Transcribes paper into systems; needs WhatsApp + mobile for speed, web for deeper work |
| **Pak Haji Ahmad** | Anggota | No self-service view of savings / purchase history |
| **Agus Wijaya** | Ketua Koperasi | No real-time sales visibility between monthly meetings |
| **Ratna Dewi** | Bendahara / Admin | Manual reconciliation before RAT; needs export + finance views |

---

## Selected Theme

**Accelerating Digital Transformation for Rural Economic Institutions.**

KopTumbuh closes the gap between government digitalization mandates (SIMKOPDES) and rural cooperative reality. It does **not** replace SIMKOPDES — it captures data at the source (WhatsApp) and **exports** to the required formats.

---

## Solution Overview

KopTumbuh is a **three-surface system** on one API:

```
  WhatsApp (Evolution)     Web Dashboard (Next.js)     Mobile (Flutter)
           \                      |                        /
            \                     |                       /
             v                    v                      v
                    Backend API (FastAPI :8100 host / :8000 in Docker)
              WhatsApp pipeline · Gemini · Validation
              Celery workers · PostgreSQL · Redis · MinIO
```

**How it works in 30 seconds:**

1. Operator sends WhatsApp: *“Bu Siti beli 2 Beras 5kg, 1 Minyak Goreng 2L, bayar tunai”*
2. AI extracts entities (products, quantities, customer, payment) — **not** prices/totals
3. System looks up **database prices** (**No AI Math**)
4. Operator gets confirmation: **YA / UBAH / BATAL**
5. Reply `YA` → ledger + inventory updated atomically
6. Dashboard / mobile show sales, stock alerts, recommendations

**If WhatsApp is down:** Web **POS Kasir → Demo 1-klik → Dashboard Refresh** (&lt;60s). See [DEMO.md](DEMO.md).

---

## Features

### Core transaction flow

- WhatsApp recording — **text, voice, photo**
- Gemini 2.5 Flash multimodal extraction (Indonesian)
- Human-in-the-loop — **YA / UBAH / BATAL**
- Deterministic math — DB prices only
- Atomic commit — `transaksi_penjualan` + `barang_keluar` + inventaris
- Intent branching — sale, restock draft, stock adjust, knowledge Q&A
- Web POS fallback (no Gemini required)

### Supply chain intelligence

- Stockout / restock recommendations (ADS + lead time)
- Slow-moving detection
- Supplier list, restock plan, purchase history, draft POs (Celery beat)

### Member engagement

- RFM segmentation (`DIAMOND` / `EMAS` / `PERAK` / `PERUNGGU` / `TIDAK_AKTIF`)
- Winback / onboarding / milestone WhatsApp jobs
- Anggota self-service: my-transactions, my-savings, my-loans

### Government compliance

- SIMKOPDES-shaped core schema + KopTumbuh extensions
- One-click export — CSV / XLSX / JSON → MinIO + `ekspor_log`
- RAT / SHU views on dashboard

### Multi-tenant & roles

- Roles: `OPERATOR`, `KETUA`, `BENDAHARA`, `PEMBINA`, `ADMIN`, `ANGGOTA`
- Isolation via `koperasi_ref` (HUB: `referensi_koperasi_wilayah`)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend API | Python / FastAPI | Async REST + OpenAPI |
| Workers | Celery + Redis | Parse, validate, recs, supply, RFM, backup |
| Database | PostgreSQL 15 | Government-compatible `koptumbuh` schema |
| Cache / queue | Redis 7 | Celery, sessions, rate limit, idempotency |
| Object storage | MinIO | Media, exports, backups |
| WhatsApp | Evolution API | Self-hosted, QR pairing |
| AI | Google Gemini 2.5 Flash | Text / voice / OCR |
| Web | Next.js 14 + Tailwind + TanStack Query + Recharts | Admin analytics |
| Mobile | Flutter + Dio + secure storage | Operator + anggota |
| Auth | JWT + bcrypt | Web + mobile |
| Infra | Docker Compose | Postgres, Redis, MinIO, Evolution, API, worker, beat |

Additive SQL: `database/migrations.sql` (views, loans, delivery, etc.).

---

## Architecture

### System flow

```
WhatsApp user (operator)
        │ text / voice / photo
        ▼
Evolution API ──webhook──► FastAPI (rate limit, idempotency, pesan_masuk)
                                │
                                ▼
                         Celery: route → Gemini → validate → confirm
                                │
                    YA ─────────┼─────────► atomic DB commit
                                │
              PostgreSQL ◄──────┴──────► Redis session (15 min TTL)
                     ▲
         Web + Mobile REST clients
```

### Database HUB pattern

All operational tables FK to **`referensi_koperasi_wilayah`** (central hub), which links to `referensi_wilayah`. This supports region queries, historical integrity, and SIMKOPDES-shaped export.

Full DDL: `database/koptumbuh_updated_minimal_data_model.sql`  
Seed: `database/seed_demo.sql`  
Views / extensions: `database/migrations.sql` (~20 analytical / ops views including reconciliation, RFM, SHU, safety stock).

---

## How to Run

### Prerequisites

- Docker Desktop  
- Node.js 18+ (web)  
- Optional: Flutter (mobile), `GEMINI_API_KEY` (live WhatsApp AI only)

### Quick start (~5 minutes)

```bash
# 1. Configure
cd backend
cp .env.example .env
# Set GEMINI_API_KEY for WhatsApp AI path (optional for POS demo)

# 2. Start stack (API + worker + beat + Postgres + Redis + MinIO + Evolution)
docker compose up -d --build

# 3. Health (host port 8100 → container 8000)
curl -s http://localhost:8100/health

# 4. Fresh volumes auto-apply migrations via 03_migrations.sql (no manual step)
#    Only re-run migrations.sql manually if upgrading an old volume.

# 5. Web dashboard
cd ../web-dashboard
cp .env.local.example .env.local   # API_INTERNAL_URL=http://localhost:8100
npm install
npm run dev
# http://localhost:3000
# Or full stack web: docker compose (repo root) → http://localhost:8101
```

OpenAPI: http://localhost:8100/docs · Evolution: http://localhost:8082  

Full deploy notes: **[DEPLOY.md](DEPLOY.md)**

### Mobile (optional)

```bash
cd mobile-app
flutter pub get
flutter run
# Emulator API base: http://10.0.2.2:8000/api/v1
```

### Smoke / demo readiness (no WhatsApp)

```bash
bash backend/scripts/api_tests.sh
bash backend/scripts/demo_ready.sh
# Windows: cd backend\scripts; .\demo_ready.ps1
cd backend && pytest tests/ -v
```

### Development without WhatsApp

**Preferred:** Dashboard → **POS Kasir → Demo 1-klik → Refresh**.

Or webhook (needs worker + Gemini for full YA path):

```bash
curl -s -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "apikey: koptumbuh-evolution-key" \
  -d '{
    "event": "messages.upsert",
    "data": {
      "key": {"id": "DEV-001", "remoteJid": "628123456003@s.whatsapp.net"},
      "message": {
        "conversation": "Bu Siti beli 2 Beras Premium 5kg dan 1 Minyak Goreng 2L, bayar tunai",
        "messageType": "conversation"
      }
    }
  }'
```

Then send `YA` with a **new** message id after confirmation is queued. Details: **[DEMO.md](DEMO.md)**.

---

## Demo Account

| Role | Phone | Password | Access |
|------|-------|----------|--------|
| Operator (Budi) | `628123456003` | `kop123` | WhatsApp / mobile / POS / most ops |
| Ketua (Agus) | `628123456001` | `kop123` | Dashboard (admin-capable roles) |
| Bendahara (Ratna) | `628123456002` | `kop123` | Finance / export oriented |

**Demo cooperative:** Koperasi Tumbuh Bersama — Desa Jonggol, Kec. Jonggol, Kab. Bogor, Jawa Barat (`KOP-JasaAI-A1B2C3D4E5F6`).

**Pre-loaded seed:** products + inventaris, members + savings, sample transactions, supplier, RAT/docs as in `seed_demo.sql`.

### Judge docs

| Doc | Use |
|-----|-----|
| [JUDGES_ONE_PAGER.md](JUDGES_ONE_PAGER.md) | One-page summary |
| [DEMO.md](DEMO.md) | 5-min Path A/B/C runbook |
| [QA_CARDS.md](QA_CARDS.md) | Live Q&A |
| [PITCH_DECK.md](PITCH_DECK.md) | Full pitch narrative |
| [VALIDATION_CHECKLIST.md](VALIDATION_CHECKLIST.md) | Architecture sign-off |

---

## Data Model

Government-compatible schema `koptumbuh` with core SIMKOPDES-shaped tables plus KopTumbuh extensions:

| Group | Description |
|-------|-------------|
| Master & reference | Wilayah, document/outlet types, commodities |
| Identity & organization | Profil, pengurus, karyawan, dokumen, KBLI, aset, gerai |
| Members | Anggota, simpanan, pinjaman (extension) |
| Operations | Produk, inventaris, barang masuk/keluar, transaksi |
| Finance & applications | Bank, modal, pengajuan_* |
| Village & governance | Komoditas/profil desa, RAT |
| KopTumbuh extensions | Users, WA messages, parsing, confirmations, suppliers, recommendations, notifications, adjustments, mapping, export logs, PO, deliveries, harga_pasar, … |

**Analytical views (examples):** `v_stok_terhitung`, `v_rekonsiliasi_stok`, `v_penjualan_harian`, `v_produk_terlaris`, `v_aktivitas_anggota`, plus migrations views (`v_margin_produk`, `v_segmentasi_anggota`, `v_shu_estimasi`, `v_safety_stock`, …).

---

## AI Use Disclosure

| Model | Input | Output | Safeguard |
|-------|-------|--------|-----------|
| Gemini 2.5 Flash | Free-text TX (ID) | Structured JSON (intent, items, customer, payment) | `temperature=0.0`, schema, DB entity match |
| Gemini 2.5 Flash | Voice ≤ 60s | Transcript → text parser | Duration cap; re-validate |
| Gemini 2.5 Flash | Receipt photos | Line items JSON | Low confidence → `NEEDS_REVIEW`; size caps |

**No AI Math:** AI extracts entities only. Prices and totals always come from PostgreSQL:

```python
# NOT: total = ai_response.total
db_price = float(latest_barang_masuk.harga_jual)
subtotal = quantity * db_price
```

Unmatched products / empty items → **INVALID** / review — no ledger write without **YA**.

**Data sent to Gemini:** message text, voice audio, or receipt image only. No NIK / member PII dumps in prompts. NIK masked in logs (`mask_nik`).

---

## Security & Privacy Notes

### Data protection

- NIK masking in logs (`327301******0001`)
- No PII dumps in AI prompts
- Tenant isolation via `koperasi_ref`
- JWT + role checks (`require_operator` / `require_admin`)

### Input validation

- Max text length (config)
- Max audio seconds / media size
- Webhook rate limit ~60/min/sender (Redis)
- Evolution `apikey` header when configured

### Idempotency

- Redis lock on `whatsapp_message_id` + DB unique / IntegrityError → `duplicate`

### Transaction integrity

- Confirm path commits sale + stock together; stock errors surface on WhatsApp
- Reconciliation via `v_rekonsiliasi_stok` / admin stock-reconciliation API

---

## Pilot Plan

### Phase 1 — Single co-op (Month 1)

- Location: demo co-op pattern (Jonggol / Bogor area)
- Users: Operator, Ketua, Bendahara
- Parallel run paper + WhatsApp 2 weeks
- Success: ≥90% capture via WA/POS, zero silent data loss, low match-failure rate

### Phase 2 — Multi-co-op (Month 2–3)

- 5–10 co-ops; Pembina oversight
- Success: RAT/export figures within ~2% of manual process

### Phase 3 — Deeper SIMKOPDES (Month 4–6)

- Beyond file export toward official integration **if** APIs exist
- Scale 50+ co-ops
- Success: WhatsApp/POS → government-ready artifact in &lt; 60s operationally

---

## Demo Script (5 minutes)

| Min | Focus |
|-----|--------|
| 1 | Dashboard KPIs / sales (Koperasi Tumbuh Bersama) |
| 2–3 | WhatsApp sale → confirmation → **YA** → stock (or **POS Demo 1-klik**) |
| 4 | Recommendations / slow-moving / RFM |
| 5 | SIMKOPDES export + close |

Full runbook + fallbacks: **[DEMO.md](DEMO.md)**.

---

## Team

| Name | Role | Responsibilities |
|------|------|------------------|
| _[fill]_ | Backend / AI | FastAPI, Celery, Gemini pipeline, DB |
| _[fill]_ | Frontend | Next.js dashboard, charts, POS |
| _[fill]_ | Mobile | Flutter Dio app, polling |
| _[fill]_ | Product / domain | SIMKOPDES alignment, pilot, pitch |

**Team name:** JasaAI  
**Hackathon isolation:** `KOP-JasaAI-A1B2C3D4E5F6` · extension prefix `JasaAI_`

---

## Post-MVP (explicitly out of scope for this build)

FCM push, offline TX queue, live marketplace scrape (MVP uses scheduled **simulated** `harga_pasar`), Meta Cloud API swap, cross-coop benchmarking, barcode scanner, dark mode.

---

*Built for the cooperative digitalization hackathon, July 2026. KopTumbuh is not affiliated with or endorsed by the Indonesian Ministry of Cooperatives and SMEs.*
