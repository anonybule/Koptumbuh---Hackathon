# Deploy — KopTumbuh (Team JasaAI)

Exact commands for a judge-ready stack. Target: **backend healthy in ~5 minutes**.

## Prerequisites

- Docker Desktop running  
- Node 18+ (web dashboard)  
- Optional: Flutter (mobile)  
- Optional: `GEMINI_API_KEY` (required for **live WhatsApp AI**; **not** required for POS fallback demo)

## 1. Backend (one command)

```bash
cd backend
cp .env.example .env
# Edit .env — set GEMINI_API_KEY if you will demo WhatsApp AI

docker compose up -d --build
```

Wait until healthy:

```bash
curl -s http://localhost:8000/health
# expect: "status":"ok" or "degraded" with db/redis ok
```

Apply additive migrations (views, loans, etc.) if this is a fresh volume:

```bash
# Git Bash / WSL / Linux
docker compose exec -T postgres psql -U dev_admin -d koptumbuh_dev < ../database/migrations.sql
```

PowerShell:

```powershell
Get-Content ..\database\migrations.sql -Raw | docker compose exec -T postgres psql -U dev_admin -d koptumbuh_dev
```

## 2. Web dashboard

```bash
cd web-dashboard
npm install
npm run dev
```

Open http://localhost:3000  
Login: `628123456003` / `kop123`

## 3. Smoke tests (before you present)

```bash
# Git Bash / WSL
bash backend/scripts/api_tests.sh
bash backend/scripts/demo_ready.sh
```

PowerShell:

```powershell
cd backend\scripts
.\demo_ready.ps1
```

All checks should PASS. If login fails, DB seed did not load — recreate volume:

```bash
cd backend
docker compose down -v
docker compose up -d --build
# re-apply migrations.sql
```

## 4. WhatsApp (optional — Path A)

1. Open Evolution (often http://localhost:8080)  
2. Create/pair instance with QR using API key from `.env` (`EVOLUTION_API_KEY`)  
3. Point webhook to `http://host.docker.internal:8000/api/v1/webhooks/whatsapp` (or your LAN IP)  
4. Send from paired phone as operator `628123456003` (must exist in seed)

If Evolution pairing fails → **use Path B (no WhatsApp)**.

## Fallback without WhatsApp (Path B — preferred for reliability)

| Step | Action | Time |
|------|--------|------|
| 1 | Login dashboard | 10s |
| 2 | Open **POS Kasir** → **Demo 1-klik** (or add 1 product → Simpan) | 20s |
| 3 | Dashboard → **Refresh** → new TX + KPI | 15s |
| 4 | Optional: Transaksi / Inventaris | 15s |

Or run the script (no UI):

```bash
bash backend/scripts/demo_ready.sh
```

It logs in, posts a POS sale, and prints the new transaction id.

## Services & ports

| Service | Port |
|---------|------|
| FastAPI | 8000 |
| Web | 3000 |
| Postgres | 5432 |
| Redis | 6379 |
| MinIO | 9000 / console 9001 |
| Evolution | 8080 |

## Honest note for judges

- **Day-1 demo deploy** = Docker + this checklist (technical helper OK).  
- **Village IT self-serve** = Post-MVP (managed hosting).  
- Core operator UX still needs **no new app** once WhatsApp is paired.
