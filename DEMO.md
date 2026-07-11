# Demo runbook — KopTumbuh (≤5 min)

**Goal:** Prove WhatsApp → YA → stock **or** POS → dashboard in **&lt;60 seconds**.

Credentials: `628123456003` / `kop123` · Coop `KOP-JasaAI-A1B2C3D4E5F6`

---

## Pre-flight (morning of)

```bash
cd backend && docker compose ps
curl -s http://localhost:8000/health
bash scripts/demo_ready.sh    # or: powershell scripts/demo_ready.ps1
```

Web: http://localhost:3000 logged in. Keep **POS** and **Dashboard** tabs ready.

---

## Path A — Live WhatsApp (best story)

| # | Say | Do |
|---|-----|-----|
| 1 | “Operator already uses WhatsApp.” | Send: `Bu Siti beli 1 Beras Premium 5kg, bayar tunai` |
| 2 | “AI extracts items — **not** the money.” | Show confirmation with DB prices |
| 3 | “Human is the gate.” | Reply `YA` |
| 4 | “Ledger + stock update.” | Dashboard → **Refresh** |
| 5 | Optional | Mobile Beranda / Export page |

If no confirmation in ~15s → **switch to Path B immediately**. Don’t debug Evolution on stage.

---

## Path B — No WhatsApp (most reliable)

| # | Say | Do |
|---|-----|-----|
| 1 | “Same ledger without WhatsApp — POS fallback.” | Open **/pos** |
| 2 | “One click demo sale.” | Click **Demo 1-klik** |
| 3 | “Stock decremented, TX stored.” | Click link to **Dashboard** → Refresh |
| 4 | “SIMKOPDES export ready.” | Optional **/export** |

Script alternative (terminal visible to judges):

```bash
bash backend/scripts/demo_ready.sh
```

---

## Path C — Webhook curl (shows AI pipeline without phone)

Needs `GEMINI_API_KEY` + Celery worker running.

```bash
# 1) Sale message
curl -s -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "apikey: koptumbuh-evolution-key" \
  -d "{\"event\":\"messages.upsert\",\"data\":{\"key\":{\"id\":\"DEMO-$(date +%s)\",\"remoteJid\":\"628123456003@s.whatsapp.net\"},\"message\":{\"conversation\":\"Bu Siti beli 1 Beras Premium 5kg bayar tunai\",\"messageType\":\"conversation\"}}}"

# Wait for WhatsApp confirmation (or check worker logs), then YA with a NEW id:
curl -s -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "apikey: koptumbuh-evolution-key" \
  -d "{\"event\":\"messages.upsert\",\"data\":{\"key\":{\"id\":\"YA-$(date +%s)\",\"remoteJid\":\"628123456003@s.whatsapp.net\"},\"message\":{\"conversation\":\"YA\",\"messageType\":\"conversation\"}}}"
```

If Gemini/worker is down → **Path B**.

---

## Talking points while demoing

1. **No AI Math** — prices from DB  
2. **YA gate** — trust for village finance  
3. **SIMKOPDES-shaped** schema + export  
4. **Fallback** = production thinking, not a toy  

---

## Fallback video (record once)

3 minutes: Path B full flow + one Export click. Play if venue Wi‑Fi dies. See also `JUDGES_ONE_PAGER.md`.
