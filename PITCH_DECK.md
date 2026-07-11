# KopTumbuh — Pitch Deck

## WhatsApp-First Cooperative Operations for Indonesia's 180,000 Village Cooperatives

---

## Slide 1: The Problem

### Indonesia's village cooperatives are stuck on paper.

- **180,000+ koperasi desa** serve as the economic backbone of rural Indonesia, managing daily essentials, savings, and loans for millions of members.
- Most operators run transactions **on paper or basic POS systems** — inventory counts are weeks out of date, pricing is gut-feel, and government SIMKOPDES reports are a painful monthly chore.
- **Members are disengaged** — they have no easy way to check their savings, get pricing, or communicate with their cooperative.
- **Stockouts and bad margins** eat into already-thin cooperative surpluses because nobody has real-time data.

### The operators already live in WhatsApp. The system they need should too.

---

## Slide 2: The Solution

### KopTumbuh — "Koperasi Tumbuh" (Growing Cooperative)

**A WhatsApp-first cooperative operations platform.** No app to install. No new workflow to learn.

An operator sends a chat — text, voice note, or photo of a receipt — and KopTumbuh's AI parses it into a structured transaction, confirms with a simple reply, and commits it to the ledger while updating inventory in real time.

```
Operator: "Bu Siti beli 2 Beras Premium 5kg, bayar tunai"
        ↓
   KopTumbuh AI parses the message
        ↓
   WhatsApp reply: "Konfirmasi: Beras Premium 5kg x2 @Rp75.000. Total: Rp150.000. Balas YA/UBAH/BATAL"
        ↓
Operator: "YA"
        ↓
   Transaction committed. Stock updated. Member notified.
```

**One message. One confirmation. Done.**

---

## Slide 3: Why WhatsApp?

| Barrier | WhatsApp-First Approach |
|---------|-------------------------|
| App installation | None required — operators already use WhatsApp daily |
| Training | No new interface — it's just chat |
| Internet costs | WhatsApp works on 2G, uses minimal data |
| Device requirements | Any phone that runs WhatsApp (even entry-level) |
| Adoption speed | Instant — no rollout, no classroom training |
| Member access | Members already message their cooperative on WhatsApp |

**WhatsApp has 90M+ daily active users in Indonesia.** It is the country's de facto operating system for communication and commerce.

---

## Slide 4: The Full Platform

KopTumbuh is not just a WhatsApp bot — it's a **three-platform system** covering every cooperative touchpoint:

### WhatsApp Bot (Operator Interface)
- Text, voice, and photo receipt → AI parsing → confirmation → ledger
- Stock checks, price lookups, member inquiries all via chat
- Automated broadcasts: daily prices, low-stock alerts, member milestones

### Web Dashboard (Management Interface)
- **25+ pages** of analytics, inventory, supply chain, members, finance
- Real-time dashboards with sales trends, top products, stock reconciliation
- Export to SIMKOPDES-compatible CSV/XLSX/JSON
- Multi-cooperative oversight for federations

### Flutter Mobile App (Member & Operator Interface)
- **30+ screens** for transactions, products, recommendations, savings, and AI assistant
- Member self-service: check savings, view transactions, apply for loans
- Push notifications for prices, promotions, and payment reminders

---

## Slide 5: AI Engine — Smart, But With Guardrails

### One model. Three input modes.

**Google Gemini 2.5 Flash** handles text parsing, voice transcription, and receipt OCR through a single multimodal pipeline — reducing cost and complexity.

### The "No AI Math" Rule

AI extracts **what** was sold and **how many** — but **never** the price or total. All financial values are computed from the authoritative database price list. This is our core safety principle:

> *AI hallucinates a price? It never reaches the ledger. The database is always the source of truth for money.*

### AI + Human Confirmation Loop

Every AI-parsed transaction requires a human **YA** (yes) before it commits. The operator is always the final authority:

| Response | Meaning |
|----------|---------|
| **YA** | Confirmed — commit transaction, update stock |
| **UBAH** | Wrong — discard, operator will resend |
| **BATAL** | Cancel — discard, do nothing |

---

## Slide 6: Key Features

### Core Operations
- **WhatsApp transaction pipeline** — text, voice, photo → transaction
- **Real-time inventory** — stock decremented atomically on every sale
- **Multi-product receipts** — "2 Beras Premium, 1 Minyak Goreng, 3 Gula Pasir" parsed in one message
- **Manual POS fallback** — web-based point of sale for non-WhatsApp scenarios

### Supply Chain Intelligence
- **ADS-based restock planning** — Average Daily Sales drives automatic reorder suggestions
- **Auto purchase order generation** — low stock triggers POs without human intervention
- **Supplier scorecards** — performance tracking across price, delivery time, and quality
- **E-commerce price scraping** — daily market price comparison for competitive pricing

### Member Engagement
- **RFM segmentation** — GOLD / SILVER / BRONZE / INACTIVE tiers for targeted campaigns
- **AI recommendations** — restock alerts, bundling suggestions, promotion opportunities
- **Automated broadcasts** — daily price lists, winback campaigns, onboarding messages, milestone celebrations
- **Self-service** — members check savings, loan status, and transaction history

### Compliance & Reporting
- **SIMKOPDES-compatible exports** — CSV, XLSX, JSON formats
- **Full audit trail** — every transaction, stock movement, and price change is logged
- **PII compliance** — NIK masking, role-based access control
- **Automated backups** — daily database backup to MinIO object storage

---

## Slide 7: Architecture

### Three independent codebases, one REST API

```
┌─────────────────────────────────────────────────────────┐
│                    KopTumbuh System                       │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  WhatsApp    │  │  Web Dashboard│  │  Mobile App  │   │
│  │  (Chat)      │  │  (Next.js)   │  │  (Flutter)   │   │
│  │  Evolution   │  │  Port 3000   │  │  Android/iOS │   │
│  │  API Bridge  │  │              │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │            │
│         └─────────────────┼─────────────────┘            │
│                           │                              │
│                    ┌──────▼──────┐                       │
│                    │  Backend API │                       │
│                    │  (FastAPI)  │                       │
│                    │  Port 8000  │                       │
│                    └──────┬──────┘                       │
│                           │                              │
│         ┌─────────────────┼─────────────────┐            │
│         │                 │                 │            │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐       │
│    │PostgreSQL│     │  Redis  │      │  MinIO  │       │
│    │  15      │     │   7     │      │  (S3)   │       │
│    │ 41 tables│     │ Cache/  │      │ Storage │       │
│    │ 5 views  │     │ Queue   │      │         │       │
│    └─────────┘      └─────────┘      └─────────┘       │
│                                                           │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│    │  Celery  │    │  Celery  │    │  Gemini  │         │
│    │  Worker  │    │   Beat   │    │  2.5 API │         │
│    │ (async)  │    │(scheduler)│   │  (AI/ML) │         │
│    └──────────┘    └──────────┘    └──────────┘         │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI / Celery / Redis |
| Database | PostgreSQL 15 / SQLAlchemy 2.0 / Alembic |
| AI | Google Gemini 2.5 Flash (multimodal) |
| Web Dashboard | Next.js 14 / React / Tailwind CSS / Recharts |
| Mobile | Flutter 3.x / Dio / Material 3 |
| Storage | MinIO (S3-compatible) |
| WhatsApp | Evolution API (open-source bridge) |
| Deployment | Docker Compose (7 services) |

---

## Slide 8: Market Opportunity

### The Numbers

| Metric | Value |
|--------|-------|
| Village cooperatives in Indonesia | **180,000+** |
| Cooperative members nationwide | **50+ million** |
| Total cooperative assets | **Rp 200+ trillion** |
| Villages with internet access | **75,000+** (growing) |
| WhatsApp users in Indonesia | **90+ million DAU** |

### Why Now?

1. **SIMKOPDES mandate** — the government requires all village cooperatives to digitize reporting, but most lack tools to do it efficiently.
2. **Digital infrastructure is ready** — 4G covers most of rural Java and Sumatra, and WhatsApp penetration is near-universal.
3. **AI costs have collapsed** — Gemini 2.5 Flash processes a full transaction for fractions of a rupiah, making per-transaction AI economically viable for the first time.
4. **No incumbent with WhatsApp-first UX** — existing cooperative software requires app installation, training, and devices that operators don't have.

---

## Slide 9: Business Model

### B2B SaaS for Cooperatives

| Tier | Price | Includes |
|------|-------|----------|
| **Starter** | Free | Up to 3 operators, 500 transactions/month, basic reports |
| **Tumbuh** | Rp 500K/month | Up to 10 operators, unlimited transactions, analytics, AI recommendations |
| **Maju** | Rp 1.5M/month | Unlimited operators, supply chain automation, auto-PO, priority support |
| **Federasi** | Custom | Multi-cooperative federation dashboard, white-label option, API access |

### Additional Revenue Streams

- **Transaction fees** on member savings deposits and loan payments (revenue share with cooperative)
- **Supplier marketplace** — connect cooperatives directly to distributors, take a commission
- **Data insights** — aggregated, anonymized market intelligence for government and agribusiness

---

## Slide 10: Competitive Advantage

| Feature | KopTumbuh | Existing POS | SaaS Koperasi |
|---------|-----------|-------------|---------------|
| WhatsApp-native transactions | Yes | No | No |
| Multimodal AI (text + voice + photo) | Yes | No | Limited |
| Real-time inventory | Yes | Some | Some |
| AI with guardrails (No AI Math) | Yes | N/A | No |
| SIMKOPDES-compatible exports | Yes | Manual | Partial |
| Supply chain automation | Yes | No | No |
| Member self-service (WA + app) | Yes | No | App only |
| Multi-platform (WA + Web + Mobile) | Yes | No | Some |
| RFM engagement engine | Yes | No | No |

### Our Moat

1. **The WhatsApp wedge** — operators won't switch tools once their daily workflow runs through chat. High switching cost, low churn risk.
2. **Data network effects** — the more transactions processed, the better the AI gets at product matching and the smarter the recommendations become.
3. **SIMKOPDES lock-in** — built as an extension of the government schema. If we become the reference implementation, migration cost for cooperatives drops to zero.

---

## Slide 11: Traction & Roadmap

### Hackathon Milestones (Current)

- Fully functional WhatsApp → transaction → inventory pipeline
- 25+ page web dashboard with real-time analytics
- 30+ screen Flutter mobile app
- 41 database tables with SIMKOPDES schema compatibility
- 9 automated Celery Beat scheduled tasks
- 7 test suites covering critical paths
- Docker Compose one-command deployment

### Next 3 Months

- Pilot with 3-5 village cooperatives in West Java
- Bahasa Indonesia voice model fine-tuning for regional dialects
- WhatsApp Pay integration for member savings and loan payments
- Offline queue — queue transactions when internet drops, sync when reconnected

### Next 6-12 Months

- 50+ cooperative customers
- B2B supplier marketplace MVP
- Government partnership for SIMKOPDES integration
- Federated cooperative dashboard for kabupaten-level oversight
- SMS fallback channel for areas without WhatsApp coverage

---

## Slide 12: The Ask

### We are seeking:

- **Pilot partners** — 3-5 village cooperatives willing to run KopTumbuh alongside their existing system for 3 months
- **Strategic investment** — to fund the pilot program, voice model fine-tuning, and go-to-market in West Java
- **Government introduction** — connections to Kemenkop UKM and Dinas Koperasi for SIMKOPDES alignment

### Why back this team:

- **Deep understanding of the problem** — the data model proves we understand SIMKOPDES at the schema level
- **Working product, not a slide deck** — WhatsApp pipeline, web dashboard, and mobile app are all built and demonstrable
- **Right tech, right time** — AI costs have dropped to the point where per-transaction AI for village cooperatives is viable today, not in 3 years
- **Massive underserved market** — 180,000 cooperatives, 50 million members, zero WhatsApp-first competitors

---

## Slide 13: Demo

### See it live:

```
Operator WhatsApp: 628123456003
Password: kop123
Cooperative: KOP-JasaAI-A1B2C3D4E5F6

Backend API: http://localhost:8000/docs
Web Dashboard: http://localhost:3000
```

### Demo flow:
1. Operator sends a sale message via WhatsApp
2. AI parses and returns confirmation with computed total
3. Operator replies YA — transaction commits, stock updates
4. Dashboard shows real-time sales and inventory changes
5. Mobile app reflects updated stock and transaction history

---

## Team JasaAI

**KopTumbuh** — *"Dari desa, untuk Indonesia."* (From the village, for Indonesia.)

Built with:
- Python / FastAPI / Celery / PostgreSQL
- Next.js 14 / React / Tailwind CSS
- Flutter / Dart / Material 3
- Google Gemini 2.5 Flash
- Docker / MinIO / Redis
