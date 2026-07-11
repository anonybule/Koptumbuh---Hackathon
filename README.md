# KopTumbuh — Team JasaAI

WhatsApp-first cooperative operations for village co-ops: message → AI parse → YA/UBAH/BATAL → sale + stock, with admin web dashboard and Flutter mobile app.

**Coop ref:** `KOP-JasaAI-A1B2C3D4E5F6`  
**Demo login:** `628123456003` / `kop123`

---

## Problem

Village cooperative operators already live in WhatsApp. Paper POS and delayed stock updates cause stockouts, bad margins, and weak SIMKOPDES reporting. KopTumbuh turns everyday chat into confirmed operational data.

## Solution

1. Operator sends text / voice / photo on WhatsApp.  
2. Gemini extracts intent + line items; validator matches products (exact → ILIKE → Jaccard) and uses **DB prices only**.  
3. Operator replies **YA** / **UBAH** / **BATAL**. Only YA commits `transaksi_penjualan` + `barang_keluar` + inventaris.  
4. Web dashboard and mobile app show KPIs, inventory, supply restock plans, recommendations, and SIMKOPDES export.

## Architecture (short)

| Layer | Stack |
|-------|--------|
| Gateway | Evolution API webhook → FastAPI → Redis rate limit + idempotency |
| Workers | Celery + Redis (parse, validate, confirm dispatch, recs, supply, RFM, backup) |
| Data | PostgreSQL `koptumbuh` schema + MinIO (media / exports / backups) |
| Clients | Next.js 14 dashboard + Flutter mobile |
| Export | CSV / XLSX / JSON → MinIO + `ekspor_log` (no direct SIMKOPDES write) |

See `implementation_plan.md` and `VALIDATION_CHECKLIST.md` for full layer checklist.

---

## Quick start (≈5 minutes)

### 1. Backend

```bash
cd backend
cp .env.example .env
# Set GEMINI_API_KEY (required for live AI parse)

docker compose up -d --build
```

- Health: http://localhost:8000/health  
- OpenAPI: http://localhost:8000/docs  

Apply additive migrations if needed:

```bash
# from host with psql, or via compose exec
psql "$DATABASE_URL" -f ../database/migrations.sql
```

### 2. Web dashboard

```bash
cd web-dashboard
npm install
npm run dev
```

Open http://localhost:3000 — login with demo credentials.

### 3. Mobile (optional)

```bash
cd mobile-app
flutter pub get
flutter run
```

Android emulator API base: `http://10.0.2.2:8000/api/v1`.

### 4. Smoke tests

```bash
bash backend/scripts/api_tests.sh
cd backend && pytest tests/ -v
```

---

## Demo script (≤5 minutes)

1. Pair WhatsApp via Evolution (QR in Evolution console).  
2. Send: `Bu Siti beli 2 Beras Premium 5kg, bayar tunai`  
3. Reply `YA` to the confirmation.  
4. Web dashboard → Refresh → new TX + KPI + inventory.  
5. Optional: mobile Beranda / Rekomendasi polling; Admin → Export SIMKOPDES.

### Fallback if WhatsApp is down

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"event":"messages.upsert","data":{"key":{"id":"DEMO-1","remoteJid":"628123456003@s.whatsapp.net"},"message":{"conversation":"Bu Siti beli 1 Beras Premium 5kg bayar tunai","messageType":"conversation"}}}'
```

Then post `YA` with a new message id after the confirmation session is active — or show POS + dashboard from seed data. Record a 3-minute fallback video covering the same five beats.

---

## What is included (MVP)

- Full `/api/v1/mobile/*` and `/api/v1/admin/*` contracts  
- Engines: transaction, validation, supply (ADS/PO), recommender, export, reconciliation, BI, RFM relationship, DQ normalize, backup  
- Web: analytics, inventory, supply, cooperatives, members, finance, village, knowledge, users, export, recommendations, notifications, POS, transactions  
- Mobile: Dio + secure storage, tabs, polling (10s/30s/60s), local notifications, role-aware UI  
- Tests: TC-001–006 + `api_tests.sh`

## Out of scope (Post-MVP)

FCM push, dark mode, barcode scanner, offline TX queue, Meta Cloud API swap, cross-coop benchmarking, full government SIMKOPDES parity beyond export adapter.

---

## Environment

See `backend/.env.example` for JWT, Redis, MinIO, Evolution, Gemini, and DB variables. Never commit real NIK or production secrets.

## Team

**JasaAI** — KopTumbuh hackathon build.
