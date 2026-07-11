# KopTumbuh — Pitch Deck

## WhatsApp-First Cooperative Operations for Indonesia's 180,000 Village Cooperatives

**Team:** JasaAI · **Product:** KopTumbuh · **Tagline:** *Dari desa, untuk Indonesia.*

---

## Slide 1: The Problem

### Indonesia's village cooperatives are stuck on paper.

- **180,000+ koperasi desa** serve as the economic backbone of rural Indonesia — daily essentials, savings, and loans for millions of members.
- Most operators run on **paper or basic POS** — inventory is weeks out of date, pricing is gut-feel, and SIMKOPDES reporting is a painful monthly chore.
- **Members are disengaged** — no easy way to check savings, prices, or talk to the cooperative.
- **Stockouts and bad margins** eat thin surpluses because nobody has real-time data.

### The operators already live in WhatsApp. The system they need should too.

---

## Slide 2: The Solution

### KopTumbuh — "Koperasi Tumbuh" (Growing Cooperative)

**A WhatsApp-first cooperative operations platform.** No app to install for the core workflow. No new habit to learn.

An operator sends a chat — text, voice note, or photo of a receipt — and KopTumbuh's AI parses it into a structured draft, confirms with a simple reply, and only then commits to the ledger while updating inventory.

```
Operator: "Bu Siti beli 2 Beras Premium 5kg, bayar tunai"
        ↓
   Gemini extracts intent + line items (not prices)
        ↓
   WhatsApp: "Konfirmasi… Total Rp … Balas YA / UBAH / BATAL"
        ↓
Operator: "YA"
        ↓
   transaksi_penjualan + barang_keluar + inventaris updated
```

**One message. One confirmation. Done.**

---

## Slide 3: Why WhatsApp?

| Barrier | WhatsApp-First Approach |
|---------|-------------------------|
| App installation | None for core recording — operators already use WhatsApp daily |
| Training | No new UI — it's chat |
| Internet costs | Works on low bandwidth; minimal data |
| Device requirements | Any phone that runs WhatsApp |
| Adoption speed | Instant — no classroom rollout |
| Member access | Members already message their cooperative on WhatsApp |

**WhatsApp has 90M+ daily active users in Indonesia** — the country's de facto OS for communication and commerce.

---

## Slide 4: The Full Platform (MVP)

KopTumbuh is a **three-surface system** on one REST API:

### WhatsApp (operator primary)
- Text / voice / photo → AI parse → **YA / UBAH / BATAL** → ledger
- Intent branching: sale, restock draft, stock adjust, knowledge Q&A
- Scheduled automations: price broadcast, restock recs, RFM winback / onboarding

### Web dashboard (management)
- **~23 live pages**: analytics, POS, inventory, supply, members, loans, cooperatives, RAT, finance, village, knowledge, export, users, settings
- Charts: sales, margin, slow-moving, RFM segmentation, price comparison
- SIMKOPDES-compatible export (CSV / XLSX / JSON → MinIO)

### Flutter mobile (operator + anggota)
- **~26 screens** wired to live `/mobile/*` APIs (Dio + secure tokens)
- Tabs: Beranda / Transaksi / Produk / Rekomendasi + Asisten (knowledge search)
- Polling (10s / 30s / 60s) + local notifications — **FCM is Post-MVP**

---

## Slide 5: AI Engine — Smart, With Guardrails

### One model. Three input modes.

**Google Gemini 2.5 Flash** — text extraction, voice transcription, receipt OCR in one multimodal pipeline.

### The "No AI Math" Rule

AI extracts **what** was sold and **how many** — **never** the price or total. Money always comes from the DB price list:

> *If AI hallucinates a price, it never reaches the ledger.*

### Product matching (Validation Engine)

Exact name → substring / ILIKE → token Jaccard ≥ 0.5 → stock check → then confirm.

### Human confirmation loop

| Reply | Effect |
|-------|--------|
| **YA** | Commit sale (or apply stock adjust) |
| **UBAH** | Supersede draft; operator resends |
| **BATAL** | Clear session; write nothing |

---

## Slide 6: Key Features (Honest MVP)

### Core operations
- WhatsApp pipeline: text / voice / photo → confirm → stock
- Real-time inventaris on YA (and POS / mobile manual TX)
- Multi-line messages in one parse
- **POS fallback** on web if WhatsApp is down

### Supply & intelligence
- ADS-based restock plan + auto draft POs (Celery beat)
- Recommendations: STOCKOUT_RISK / SLOW_MOVING / RESTOCK (24h dedupe)
- Market price comparison via `harga_pasar` (**MVP: simulated daily inserts**; live marketplace scrape = Post-MVP)

### Member engagement
- RFM tiers from `v_segmentasi_anggota`: **DIAMOND / EMAS / PERAK / PERUNGGU / TIDAK_AKTIF**
- Retention labels: PELANGGAN_SETIA → HILANG
- Winback / onboarding / milestone WhatsApp jobs
- Anggota self-service: my-transactions, my-savings, my-loans

### Compliance
- SIMKOPDES-shaped schema + export adapter (no fake “direct government API write”)
- NIK masking, JWT + RBAC
- Daily `pg_dump` → MinIO backups

---

## Slide 7: Architecture

```
WhatsApp (Evolution) ─┐
Web (Next.js :3000)  ─┼─► FastAPI :8000 ─► PostgreSQL (koptumbuh)
Mobile (Flutter)     ─┘         │
                                ├─ Redis (sessions, rate limit, Celery)
                                ├─ MinIO (media / exports / backups)
                                └─ Celery worker + beat + Gemini 2.5 Flash
```

### Tech stack (as shipped)

| Layer | Technology |
|-------|------------|
| Backend | Python / FastAPI / Celery / Redis |
| Database | PostgreSQL + SQLAlchemy 2.0 · additive SQL in `migrations.sql` (not Alembic for MVP) |
| AI | Google Gemini 2.5 Flash |
| Web | Next.js 14 / Tailwind / TanStack Query / Recharts |
| Mobile | Flutter / Dio / flutter_secure_storage / local notifications |
| Storage | MinIO (S3-compatible) |
| WhatsApp | Evolution API |
| Deploy | Docker Compose (API, worker, beat, Postgres, Redis, MinIO, Evolution) |

### Proof points (hackathon build)

| Metric | Value |
|--------|-------|
| API routes registered | **~99** |
| Web dashboard pages | **~23** |
| Mobile screens | **~26** (API-wired) |
| Analytical / ops views | **~20** (schema + migrations) |
| Celery beat jobs | **9** (recs, prices, briefing, PO, RFM, backup, …) |
| Integration tests | **TC-001–006** + `api_tests.sh` |
| Deploy | `docker compose up -d --build` |

---

## Slide 8: Market Opportunity

| Metric | Value |
|--------|-------|
| Village cooperatives in Indonesia | **180,000+** |
| Cooperative members nationwide | **50+ million** |
| Total cooperative assets | **Rp 200+ trillion** |
| Villages with internet access | **75,000+** (growing) |
| WhatsApp users in Indonesia | **90+ million DAU** |

### Why now?

1. **SIMKOPDES mandate** — digitize reporting; most co-ops lack usable tools.
2. **Rural connectivity + WhatsApp ubiquity** — the channel is already there.
3. **AI cost collapse** — per-TX multimodal parse is finally affordable.
4. **No WhatsApp-first incumbent** for village cooperative ops + SIMKOPDES-shaped data.

---

## Slide 9: Business Model

### B2B SaaS for cooperatives

| Tier | Price | Includes |
|------|-------|----------|
| **Starter** | Free | Up to 3 operators, 500 TX/month, basic reports |
| **Tumbuh** | Rp 500K/month | 10 operators, unlimited TX, analytics, AI recs |
| **Maju** | Rp 1.5M/month | Unlimited operators, supply automation, priority support |
| **Federasi** | Custom | Multi-coop dashboard, white-label, API |

### Later revenue (Post-MVP)

- Savings / loan payment rails (revenue share)
- Supplier marketplace commission
- Anonymized market intelligence for government / agribusiness

---

## Slide 10: Competitive Advantage

| Feature | KopTumbuh | Typical POS | SaaS Koperasi |
|---------|-----------|-------------|---------------|
| WhatsApp-native TX + YA confirm | Yes | No | No |
| Multimodal AI (text + voice + photo) | Yes | No | Limited |
| No AI Math (DB prices only) | Yes | N/A | Rare |
| Real-time inventaris | Yes | Some | Some |
| SIMKOPDES-compatible export | Yes | Manual | Partial |
| Supply / RFM engines | Yes | No | Rare |
| Web + mobile + WA | Yes | No | Some |

### Moat

1. **WhatsApp wedge** — daily habit = high switching cost  
2. **Data flywheel** — more TX → better matching & recs  
3. **Schema alignment** — built on SIMKOPDES-shaped tables, not a parallel silo  

---

## Slide 11: Traction & Roadmap

### Hackathon (today) — working MVP

- End-to-end WhatsApp → validate → YA → stock
- Web analytics + POS + export
- Mobile live against `/mobile/*`
- Docker one-command stack
- Fallback demo path if Evolution/WhatsApp is down (POS or webhook curl)

### Next 3 months (Post-MVP)

- Pilot 3–5 co-ops (West Java)
- Offline TX queue + FCM push
- Dialect-tuned voice
- Live marketplace / Bapanas price feeds (replace simulated `harga_pasar`)

### Next 6–12 months

- 50+ co-ops · supplier marketplace · deeper SIMKOPDES partnership · federasi dashboard

---

## Slide 12: The Ask

### For hackathon judges

1. **Validate the wedge** — WhatsApp-first + human confirm is the right UX for village co-ops  
2. **Score the working demo** — not a mockup: live pipeline + dashboard + mobile  
3. **Open doors** — intros to Kemenkop / Dinas Koperasi / pilot co-ops  

### For partners (after the hackathon)

- **3–5 pilot cooperatives** (3 months side-by-side with current process)  
- **Strategic capital** for pilots, GTM in West Java, and voice/offline hardening  
- **SIMKOPDES alignment** conversations with government stakeholders  

### Why this team

- Schema-level SIMKOPDES literacy (not just UI)  
- Shippable product today  
- Timing: AI unit economics finally work for village TX volume  

---

## Slide 13: Demo

### Credentials

```
Phone / login: 628123456003
Password:      kop123
Koperasi:      KOP-JasaAI-A1B2C3D4E5F6

API docs:      http://localhost:8000/docs
Dashboard:     http://localhost:3000
```

### Happy path (≤5 min)

1. Send sale text on WhatsApp  
2. Reply **YA** to confirmation  
3. Refresh web dashboard → TX + KPI + stock  
4. Optional: mobile Beranda / Transaksi  

### Fallback if WhatsApp is down

1. Web **POS Kasir** → Simpan transaksi, **or**  
2. Webhook curl (see `README.md` / `DEMO.md`) → then show dashboard  

---

## Slide 14: Team JasaAI

| Role | Focus | Name |
|------|--------|------|
| Product / Architecture | SIMKOPDES data model, MVP scope | _[fill]_ |
| Backend / AI | FastAPI, Celery, Gemini pipeline | _[fill]_ |
| Web | Next.js dashboard + analytics | _[fill]_ |
| Mobile | Flutter Dio app + polling | _[fill]_ |

*(Replace placeholders with real names before presenting.)*

**KopTumbuh** — *Dari desa, untuk Indonesia.*

---

## Slide 15: Close / CTA

### One line

**Turn WhatsApp chats into trusted cooperative ledgers — with AI that never invents the money.**

### Next step

1. Watch the 5-minute demo  
2. Try login `628123456003` / `kop123`  
3. Talk to us about a village pilot  

**Contact:** Team JasaAI · KopTumbuh  
**Repo / docs:** `README.md` · `VALIDATION_CHECKLIST.md` · OpenAPI `/docs`

Built with: FastAPI · Celery · PostgreSQL · Next.js · Flutter · Gemini 2.5 Flash · Docker · MinIO · Redis · Evolution API
