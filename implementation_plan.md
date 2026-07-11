# KopTumbuh MVP — Complete Implementation Plan

## Context

KopTumbuh upgrades Indonesia's SIMKOPDES (cooperative management system) with a WhatsApp-first transaction interface, AI-powered extraction, and supply chain intelligence. **Three components:**

| Component | Audience | Purpose |
|-----------|----------|---------|
| **Mobile App** | Anggota (members), Operators, Admins/Pembina | Members: view savings & history. Operators: WhatsApp transactions, inventory. Admins: oversight. |
| **Web Dashboard** | Operators (primary) | Desktop work — analytics, supply chain management, SIMKOPDES export, member management |
| **Backend API** | Serves all frontends | Async WhatsApp pipeline, AI parsing, PostgreSQL ledger, recommendations |

The mobile app is being built separately. This plan covers the **backend API** and **web dashboard**, with API contracts the mobile app consumes.

**Canonical schema**: `koptumbuh_updated_minimal_data_model.sql` — 40 tables, 5 views, 9 triggers, `koptumbuh` schema. **Immutable Single Source of Truth.**

**Official SIMKOPDES Database**: Shared PostgreSQL at `34.101.155.200:5432` — 1,026 cooperatives, 74K members, 14K products, 372K savings records, 38 provinces. **Team: JasaAI**. We write extension tables with `JasaAI_` prefix into the `public` schema alongside core SIMKOPDES tables.

**Schema Alignment Decision**: Local dev uses `koptumbuh` schema for isolation. The shared hackathon DB uses `public` schema (same as SIMKOPDES). Core table names are identical — no prefix. Extension tables use `JasaAI_` prefix.

**Hackathon Isolation Rule**: EVERYTHING we create is scoped to our team identity:
- **Core tables**: Our data identified by `koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6'` (no other team uses this ref)
- **Extension tables**: Prefixed `JasaAI_` in table name (no other team has this prefix)
- **Views**: Prefixed `JasaAI_v_` in view name
- **Transactions**: All use `KOP-JasaAI-` prefix in IDs
- **100 other teams** have their own prefixes — zero data collision risk

All ID formats, status values, and data conventions match the official SIMKOPDES patterns so that if KopTumbuh becomes the official upgrade, there is zero migration needed — our data IS their data.

---

## Project Boundaries — Three Separate Codebases, One API

KopTumbuh is **not a monolith**. It is three independent projects that communicate exclusively through REST API contracts. They can be built in parallel by different people. They share zero code.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      KopTumbuh System                                │
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐ │
│  │   Backend API    │   │  Web Dashboard   │   │   Mobile App     │ │
│  │                  │   │                  │   │                  │ │
│  │  Built in THIS   │◀──│  Built in THIS   │   │  Built SEPARATELY│ │
│  │  plan            │   │  plan            │   │  (by user)       │ │
│  │                  │──▶│                  │   │                  │ │
│  │  FastAPI + Celery│   │  Next.js 14      │   │  Flutter          │ │
│  │  Port 8000       │   │  Port 3000       │   │  Mobile OS        │ │
│  │                  │   │                  │   │                  │ │
│  │  Owns: DB, Redis,│   │  Consumes:       │   │  Consumes:       │ │
│  │  MinIO, AI,      │   │  /api/v1/admin/* │   │  /api/v1/mobile/*│ │
│  │  WhatsApp pipe   │   │  /api/v1/auth/*  │   │  /api/v1/auth/*  │ │
│  └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘ │
│           │                      │                      │           │
│           └──────────────────────┴──────────────────────┘           │
│                          │                                          │
│              All communication via REST API only                     │
│              No shared code, no shared state, no direct DB access    │
└─────────────────────────────────────────────────────────────────────┘
```

### What each project owns

| Boundary | Backend API | Web Dashboard | Mobile App |
|----------|-------------|---------------|------------|
| **Codebase** | `backend/` (Python) | `web-dashboard/` (TypeScript) | Separate repo (Flutter) |
| **Database access** | **Yes** — direct PostgreSQL connection | **No** — API only | **No** — API only |
| **Redis access** | **Yes** — Celery + session state | **No** | **No** |
| **Environment variables** | DB, Redis, MinIO, Gemini, Evolution, JWT | `NEXT_PUBLIC_API_URL` only | API base URL only |
| **Deployment** | Docker Compose (API + worker + beat + services) | Vercel / Netlify / static export | App Store / Play Store / APK |
| **Auth responsibility** | Issues + validates JWT tokens | Stores token, handles refresh, protects routes | Stores token, handles refresh |
| **API namespace** | Serves all endpoints | Consumes `/api/v1/admin/*` | Consumes `/api/v1/mobile/*` |

### The integration surface

The backend API is the **only** integration point. The web dashboard and mobile app never:
- Connect directly to PostgreSQL, Redis, or MinIO
- Share authentication state (each stores its own JWT)
- Import code from each other or from the backend
- Depend on each other's deployment

The API contracts in this document (both `/mobile/` and `/admin/` endpoints with exact request/response shapes) are the **binding contract**. As long as those contracts are honored, all three projects can be built, tested, and deployed independently.

---

## Technology Stack

### Backend API

| Concern | Choice | Why |
|---------|--------|-----|
| Framework | **FastAPI** (Python 3.11+) | Async, Pydantic validation, auto OpenAPI docs for both frontend teams |
| Workers | **Celery** + Redis broker + **Celery Beat** | Mature, periodic task scheduler built in |
| Database | **PostgreSQL 15** | Already specified in canonical schema |
| ORM | **SQLAlchemy 2.0** (async) + Alembic | Industry standard, async sessions |
| Cache / Queue | **Redis 7** | Celery broker + session state |
| Object storage | **MinIO** (S3-compatible) | Self-hosted MVP, swap to S3 later |
| AI | **Google Gemini SDK** (`google-genai`) | Gemini 2.5 Flash — text extraction, image/receipt OCR, audio transcription (single multimodal model) |
| Auth | **JWT** (python-jose) + bcrypt | Stateless, mobile + web compatible |

### Web Dashboard

| Concern | Choice | Why |
|---------|--------|-----|
| Framework | **Next.js 14** (App Router) | SSR for analytics, React ecosystem |
| Styling | **Tailwind CSS** + shadcn/ui | Accessible components, rapid development |
| State | **TanStack Query** | Auto cache/invalidation for API data |
| Charts | **Recharts** | Lightweight, React-native |
| Tables | **TanStack Table** | Sort, filter, paginate |

---

## Project Directory Structure

```
Koptumbuh - Hackathon/
├── backend/
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── .env.example
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_koptumbuh_schema.py
│   ├── scripts/
│   │   ├── verify_infra.py
│   │   ├── seed_demo.py
│   │   └── demo_flow.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── core.py               # referensi_wilayah, koperasi_wilayah, profil_koperasi
│   │   │   ├── organization.py       # pengurus, karyawan, dokumen, kbli, aset, gerai
│   │   │   ├── members.py            # anggota, simpanan
│   │   │   ├── products.py           # produk, inventaris, barang_masuk, barang_keluar
│   │   │   ├── transactions.py       # transaksi_penjualan
│   │   │   ├── finance.py            # akun_bank, modal, pengajuan_*, pinjaman
│   │   │   ├── village.py            # referensi_komoditas_desa, referensi_profil_desa, rat
│   │   │   ├── operations.py         # banner, pengaduan
│   │   │   └── koptumbuh.py          # Extension tables
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py             # Standard response envelope, pagination
│   │   │   ├── webhook.py
│   │   │   ├── transaction.py
│   │   │   ├── dashboard.py
│   │   │   └── auth.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       ├── auth.py
│   │   │       ├── webhooks.py
│   │   │       ├── mobile/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── transactions.py
│   │   │       │   ├── products.py
│   │   │       │   ├── restock.py
│   │   │       │   ├── members.py
│   │   │       │   ├── customers.py
│   │   │       │   ├── savings.py
│   │   │       │   ├── recommendations.py
│   │   │       │   ├── notifications.py
│   │   │       │   └── profile.py
│   │   │       └── admin/
│   │   │           ├── __init__.py
│   │   │           ├── dashboard.py
│   │   │           ├── supply_chain.py
│   │   │           ├── members.py
│   │   │           ├── cooperatives.py
│   │   │           ├── organization.py
│   │   │           ├── assets.py
│   │   │           ├── finance.py
│   │   │           ├── village.py
│   │   │           ├── applications.py
│   │   │           ├── export.py
│   │   │           ├── users.py
│   │   │           ├── knowledge.py
│   │   │           ├── loans.py
│   │   │           ├── employees.py
│   │   │           ├── banners.py
│   │   │           ├── helpdesk.py
│   │   │           └── wilayah.py
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── celery_beat.py
│   │   │   ├── router.py
│   │   │   ├── audio.py
│   │   │   ├── vision.py
│   │   │   ├── parser.py
│   │   │   ├── validator.py
│   │   │   ├── confirmer.py
│   │   │   ├── dispatcher.py
│   │   │   ├── recommendations.py
│   │   │   └── export_worker.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ai_service.py
│   │   │   ├── whatsapp_service.py
│   │   │   ├── media_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── export_service.py
│   │   │   ├── math_service.py
│   │   │   └── state_machine.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── pii.py
│   │       ├── idempotency.py
│   │       └── http.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_webhook.py
│       ├── test_parser.py
│       ├── test_confirmation.py
│       ├── test_reconciliation.py
│       └── test_export.py
│
├── web-dashboard/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── middleware.ts
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── layout.tsx
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── page.tsx
│   │       ├── analytics/
│   │       │   ├── page.tsx
│   │       │   ├── stock/
│   │       │   │   └── page.tsx
│   │       │   ├── margin/
│   │       │   │   └── page.tsx
│   │       │   ├── slow-moving/
│   │       │   │   └── page.tsx
│   │       │   ├── active-members/
│   │       │   │   └── page.tsx
│   │       │   ├── shu/
│   │       │   │   └── page.tsx
│   │       │   ├── benchmark/
│   │       │   │   └── page.tsx
│   │       │   └── revenue-breakdown/
│   │       │       └── page.tsx
│   │       ├── supply-chain/
│   │       │   ├── page.tsx
│   │       │   ├── [supplierId]/
│   │       │   │   └── page.tsx
│   │       │   ├── restock-plan/
│   │       │   │   └── page.tsx
│   │       │   ├── purchase-history/
│   │       │   │   └── page.tsx
│   │       │   ├── supplier-scorecard/
│   │       │   │   └── page.tsx
│   │       │   └── purchase-orders/
│   │       │       └── page.tsx
│   │       ├── cooperatives/
│   │       │   ├── page.tsx
│   │       │   └── [koperasiId]/
│   │       │       ├── page.tsx
│   │       │       ├── outlets/
│   │       │       │   └── page.tsx
│   │       │       ├── assets/
│   │       │       │   └── page.tsx
│   │       │       ├── documents/
│   │       │       │   └── page.tsx
│   │       │       └── rat/
│   │       │           └── page.tsx
│   │       ├── members/
│   │       │   ├── page.tsx
│   │       │   ├── [anggotaId]/
│   │       │   │   └── page.tsx
│   │       │   └── segmentation/
│   │       │       └── page.tsx
│   │       ├── rat/
│   │       │   ├── page.tsx
│   │       │   ├── [id]/
│   │       │   │   └── page.tsx
│   │       │   ├── compare/
│   │       │   │   └── page.tsx
│   │       │   └── generate/
│   │       │       └── page.tsx
│   │       ├── village/
│   │       │   ├── page.tsx
│   │       │   └── [kode_wilayah]/
│   │       │       └── page.tsx
│   │       ├── finance/
│   │       │   ├── page.tsx
│   │       │   ├── capital/
│   │       │   │   └── page.tsx
│   │       │   └── applications/
│   │       │       └── page.tsx
│   │       ├── village/
│   │       │   └── page.tsx
│   │       ├── knowledge/
│   │       │   └── page.tsx
│   │       ├── export/
│   │       │   └── page.tsx
│   │       ├── pos/
│   │       │   └── page.tsx
│   │       ├── delivery/
│   │       │   ├── page.tsx
│   │       │   └── [id]/
│   │       │       └── page.tsx
│   │       ├── loans/
│   │       │   ├── page.tsx
│   │       │   ├── [loanId]/
│   │       │   │   └── page.tsx
│   │       │   └── create/
│   │       │       └── page.tsx
│   │       ├── employees/
│   │       │   ├── page.tsx
│   │       │   └── [employeeId]/
│   │       │       └── page.tsx
│   │       ├── banners/
│   │       │   └── page.tsx
│   │       ├── helpdesk/
│   │       │   ├── page.tsx
│   │       │   └── [id]/
│   │       │       └── page.tsx
│   │       ├── wilayah/
│   │       │   └── page.tsx
│   │       └── settings/
│   │           ├── page.tsx
│   │           ├── printer/
│   │           │   └── page.tsx
│   │           └── users/
│   │               └── page.tsx
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── dashboard-shell.tsx
│   │   ├── charts/
│   │   │   ├── sales-trend.tsx
│   │   │   ├── top-products.tsx
│   │   │   └── stock-health.tsx
│   │   ├── tables/
│   │   │   ├── data-table.tsx
│   │   │   └── status-badge.tsx
│   │   └── forms/
│   │       ├── login-form.tsx
│   │       └── export-form.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── utils.ts
│   └── hooks/
│       ├── use-auth.ts
│       ├── use-dashboard.ts
│       └── use-export.ts
│
├── database/
│   ├── koptumbuh_updated_minimal_data_model.sql
│   └── seed_demo.sql
│
└── docs/
    ├── sql_comparison.md
    ├── plan_review.md
    └── api-contracts.md
```

---

## Standard API Envelope

Every response uses a consistent format. This is critical — both frontend teams build against this contract.

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 47,
    "total_pages": 3
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Produk 'Kopi Arabika' tidak ditemukan dalam katalog.",
    "details": { "extracted_name": "Kopi Arabika", "closest_match": "Kopi Bubuk 200g" }
  }
}
```

### Pagination Standard

All list endpoints accept `?page=1&per_page=20` (default 20, max 100) and return the `meta` object above.

---

## Complete API Contract

### Authentication

| Method | Endpoint | Body | Response | Auth |
|--------|----------|------|----------|------|
| POST | `/api/v1/auth/login` | `{ "phone", "password" }` | `{ access_token, refresh_token, user }` | No |
| POST | `/api/v1/auth/refresh` | `{ "refresh_token" }` | `{ access_token, refresh_token }` | No |

### Webhook (WhatsApp Inbound)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/webhooks/whatsapp` | Verification challenge (hub.mode + hub.verify_token) |
| POST | `/api/v1/webhooks/whatsapp` | Receive message, return 200 within 500ms |

### Mobile API (`/api/v1/mobile/`) — Three User Roles

The mobile app serves three audiences. All share `/mobile/*` — the backend enforces role-based access per endpoint.

| Role | Who | Primary Use |
|------|-----|-------------|
| **Anggota** (Member) | Cooperative members who contribute savings & shop | View own savings, personal transaction history, receive recommendations, self-service profile |
| **Operator** | Daily cashiers / counter staff | WhatsApp & manual transaction recording, stock check, restock, savings deposits, customer lookup |
| **Admin / Pembina** | Regional coaches, system admins | Multi-cooperative oversight, member management, analytics, export |

| Method | Endpoint | Purpose | Role |
|--------|----------|---------|
| GET | `/mobile/dashboard/summary` | Today's sales, alerts count, pending recs | O, P |
| GET | `/mobile/products` | Product catalog (paginated, search `?q=`) | A, O, P |
| GET | `/mobile/products/{id}/stock` | Current stock + stock history for a product | O, P |
| GET | `/mobile/transactions` | Sales history (`?date_from=&date_to=&page=`) | O, P |
| GET | `/mobile/transactions/{id}` | Single transaction with line items | O, P |
| POST | `/mobile/transactions` | **Manual transaction entry** (non-WhatsApp fallback) | O |
| POST | `/mobile/restock` | **Record incoming goods** (barang_masuk_produk + update inventaris) | O |
| GET | `/mobile/restock` | Restock history | O, P |
| GET | `/mobile/members/search` | Search members (`?q=name or NIK`) | O, P |
| GET | `/mobile/members/{id}` | Member detail + savings + transaction history | O, P |
| GET | `/mobile/customers` | Walk-in customer list | O |
| POST | `/mobile/customers` | **Add walk-in customer** (pelanggan_koptumbuh) | O |
| GET | `/mobile/savings` | All member savings list (`?anggota_ref=`) | O, P |
| POST | `/mobile/savings` | **Record member savings deposit** (simpanan_anggota) | O |
| GET | `/mobile/recommendations` | AI recommendations feed (`?status=NEW`) | A, O, P |
| PATCH | `/mobile/recommendations/{id}/status` | Mark as READ / ACCEPTED / REJECTED | O, P |
| GET | `/mobile/messages` | WhatsApp message history | O, P |
| GET | `/mobile/messages/{id}` | Single message + parsing result | O, P |
| GET | `/mobile/notifications` | Notification history | A, O, P |
| GET | `/mobile/profile` | Current user profile + koperasi info | A, O, P |
| PATCH | `/mobile/profile` | Update own profile (name, phone, password) | A, O, P |
| GET | `/mobile/my-transactions` | **Anggota: own purchase history** | A |
| GET | `/mobile/my-savings` | **Anggota: own savings balance & history** | A |
| GET | `/mobile/my-loans` | **Anggota: own active & past loans** | A |
| GET | `/mobile/deliveries` | **Kurir: assigned deliveries, status updates** | O |
| PATCH | `/mobile/deliveries/{id}/status` | **Kurir: mark delivery DIKIRIM or TIBA** | O |

### Admin API (`/api/v1/admin/`) — Pembina/Admin Role

**Dashboard & Analytics:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/dashboard/kpi` | Aggregate KPIs across all cooperatives |
| GET | `/admin/dashboard/sales` | Sales trends from `v_penjualan_harian` |
| GET | `/admin/dashboard/top-products` | Top products from `v_produk_terlaris` |
| GET | `/admin/dashboard/stock-reconciliation` | Mismatches from `v_rekonsiliasi_stok` |
| GET | `/admin/dashboard/member-activity` | Engagement from `v_aktivitas_anggota` |

**Cooperatives & Organization:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/cooperatives` | All cooperatives (paginated) |
| GET | `/admin/cooperatives/{ref}` | Single cooperative full detail |
| GET | `/admin/cooperatives/{ref}/outlets` | Gerai list for cooperative |
| GET | `/admin/cooperatives/{ref}/board` | Pengurus (board/management) list |
| GET | `/admin/cooperatives/{ref}/employees` | Karyawan list |
| GET | `/admin/cooperatives/{ref}/assets` | Aset list |
| GET | `/admin/cooperatives/{ref}/documents` | Legal documents (dokumen_koperasi) |
| GET | `/admin/cooperatives/{ref}/rat` | RAT (Annual Member Meeting) records |
| GET | `/admin/cooperatives/{ref}/kbli` | KBLI classifications |
| GET | `/admin/cooperatives/{ref}/capital` | Modal/capital records |

**Members:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/members` | Cross-cooperative member list |
| GET | `/admin/members/{id}` | Member detail + activity + savings |

**Supply Chain:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/suppliers` | Supplier list |
| POST | `/admin/suppliers` | Add supplier |
| PATCH | `/admin/suppliers/{id}` | Update supplier (lead time, payment terms, status) |
| GET | `/admin/suppliers/{id}` | Supplier detail + order history + products + on-time delivery % |
| GET | `/admin/suppliers/{id}/orders` | Purchase history from this supplier (barang_masuk) |
| GET | `/admin/restock-plan` | Products needing restock: stock, ADS, days left, suggested qty, supplier |
| GET | `/admin/purchase-history` | All barang_masuk records (filterable by supplier, date, product) |
| POST | `/admin/purchase-history` | Record purchase/restock (barang_masuk + update inventaris) |

**Inventory & Stock:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/inventory` | All products with stock levels, low stock flags |
| GET | `/admin/inventory/{id}` | Product stock detail + movement history chart data |
| GET | `/admin/inventory/{id}/movements` | Combined barang_masuk + barang_keluar for this product |
| GET | `/admin/inventory/adjustments` | penyesuaian_stok audit trail |
| POST | `/admin/inventory/adjustments` | Record manual stock adjustment |

**Finance & Applications:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/finance/bank-accounts` | akun_bank_koperasi list |
| GET | `/admin/finance/capital` | modal_koperasi list |
| GET | `/admin/applications/bank-account` | pengajuan_rekening_bank |
| GET | `/admin/applications/financing` | pengajuan_pembiayaan |
| GET | `/admin/applications/partnership` | pengajuan_kemitraan |
| GET | `/admin/applications/domain` | pengajuan_domain |

**Village Data:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/village/commodities` | referensi_komoditas_desa |
| GET | `/admin/village/profiles` | referensi_profil_desa |

**Content & Users:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/knowledge` | Artikel pengetahuan list |
| POST | `/admin/knowledge` | Create article |
| PATCH | `/admin/knowledge/{id}` | Update article |
| DELETE | `/admin/knowledge/{id}` | Delete article |
| GET | `/admin/users` | User management (pengguna_koptumbuh) |
| POST | `/admin/users` | Create user |
| PATCH | `/admin/users/{id}` | Update role/status |
| GET | `/admin/notifications` | All notifications (filterable) |
| GET | `/admin/recommendations` | All recommendations (filterable) |

**Export:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/admin/export/simkopdes` | Trigger SIMKOPDES export job |
| GET | `/admin/export/history` | Export history from ekspor_log |
| GET | `/admin/export/download/{id}` | Download exported file |

---

---

## Mobile App Specification (Built Separately by User)

The mobile app is the **primary operator interface**. It is a Flutter app that consumes the `/api/v1/mobile/*` endpoints. It is NOT a WhatsApp client — operators use regular WhatsApp to send transaction messages. The mobile app is where they view results, manage inventory, act on recommendations, and manually enter data when WhatsApp isn't practical.

### Screen Map & Navigation

```
┌─────────────────────────────────────────────────────────────┐
│                      TAB NAVIGATION                          │
│  [Beranda]    [Transaksi]    [Produk]    [Rekomendasi]      │
└─────────────────────────────────────────────────────────────┘

BERANDA (Home)                    TRANSAKSI (Transactions)
┌──────────────────────┐          ┌──────────────────────┐
│ Koperasi Tumbuh      │          │ 🔍 Search...      📅 │
│ Bersama              │          │                      │
│                      │          │ TRX-20260710-ABC123  │
│ 💰 Rp 1.580.000      │          │ Bu Siti              │
│   Penjualan Hari Ini │          │ 2 item · Rp 158.000  │
│                      │          │ 10 Jul · Cash     ✅ │
│ 📊 12 Transaksi      │          │                      │
│                      │          │ TRX-20260709-DEF456  │
│ ⚠️  3 Stok Menipis   │          │ Pelanggan Umum       │
│                      │          │ 1 item · Rp 52.000   │
│ 💡 5 Rekomendasi     │          │ 09 Jul · Cash     ✅ │
│                      │          │                      │
│ 📋 Transaksi Terakhir│          │ [Tambah Manual] +    │
│  ...                 │          └──────────────────────┘
└──────────────────────┘
                               
PRODUK (Products)                 REKOMENDASI (Recommendations)  
┌──────────────────────┐          ┌──────────────────────┐
│ 🔍 Cari produk...    │          │ ⚠️ HIGH              │
│                      │          │ Restock Telur 1kg    │
│ Beras Premium 5kg    │          │ dalam 2 hari         │
│ Stok: 43 · Rp 65.000 │          │ Stok 12 · Pesan 18  │
│                      │          │           [Pesan]   │
│ Minyak Goreng 2L     │          │                      │
│ Stok: 26 · Rp 28.000 │          │ 💡 MEDIUM            │
│                      │          │ Bundling: Beras +    │
│ Gula Pasir 1kg       │          │ Minyak diskon 5%     │
│ Stok: 24 · Rp 14.000 │          │           [Lihat]   │
│                      │          │                      │
│ Telur Ayam 1kg ⚠️     │          │ 🟡 LOW               │
│ Stok: 12 · Rp 27.000 │          │ Mie Instan tidak     │
│                      │          │ terjual 14 hari      │
│ [+ Restock Manual]   │          │           [Promo]   │
└──────────────────────┘          └──────────────────────┘

PROFILE (from header)
┌──────────────────────┐
│ 👤 Budi Santoso      │
│    Operator Kasir    │
│    628123456003      │
│                      │
│ 📝 Riwayat Pesan WA  │
│ 🔔 Notifikasi        │
│ ⚙️  Pengaturan        │
│ 🚪 Keluar            │
└──────────────────────┘
```

### Key User Flows

**Flow 1: Operator records transaction via WhatsApp (primary flow)**

The app is NOT involved in recording. This is the operator's mental model:

1. Customer comes to the counter: *"Bu Siti beli 2 Beras 5kg, 1 Minyak Goreng 2L, bayar tunai"*
2. Operator opens **WhatsApp** (regular app) on their phone
3. Operator sends the message to the cooperative's WhatsApp number (the one paired with Evolution API)
4. WhatsApp delivers → Evolution API → our backend → AI parsing → validation
5. Operator receives a WhatsApp reply: *"Konfirmasi: Beras 5kg 2×65.000=130.000... YA/UBAH/BATAL"*
6. Operator replies `YA` in WhatsApp
7. Transaction committed, inventory updated
8. Operator can open the KopTumbuh mobile app later to view transaction history, check stock, see recommendations

The mobile app **polls** `GET /mobile/messages` every 10 seconds. New messages with status `PARSED` or `CONFIRMED` appear in the message history. This is read-only for the operator — the confirmation happens in WhatsApp.

**Flow 2: Operator checks stock from mobile app**

1. Open KopTumbuh app → tab Produk
2. See all products with stock levels
3. Products below threshold flagged with ⚠️
4. Tap product → detail: stock history, recent sales, supplier info

**Flow 3: Operator manually records transaction (WhatsApp offline fallback)**

1. Open KopTumbuh app → tab Transaksi → tap [+ Tambah Manual]
2. Fill form: customer name (search/select), products (search + qty), payment method
3. Submit → `POST /mobile/transactions` → committed directly (no AI, no confirmation needed — manual entry)
4. Transaction appears in history immediately

**Flow 4: Operator records restock/supplies received**

1. Open KopTumbuh app → tab Produk → tap [+ Restock Manual]
2. Select supplier, select products with quantities and purchase prices
3. Submit → `POST /mobile/restock` → barang_masuk created, inventory incremented

**Flow 5: Operator acts on recommendation**

1. Receive WhatsApp notification: *"Stok Telur Ayam 1kg menipis. Tersisa 12. Pesan sekarang ke PT Pangan Sejahtera?"*
2. Open KopTumbuh app → tab Rekomendasi
3. See the STOCKOUT_RISK recommendation
4. Tap [Pesan] → marks recommendation as ACCEPTED via `PATCH /mobile/recommendations/{id}/status`
5. (Future: auto-generate purchase order to supplier)

**Flow 6: Member savings deposit**

1. Member comes in to pay monthly savings
2. Operator opens app → search member → tap "Catat Simpanan"
3. Enter amount → `POST /mobile/savings` → simpanan_anggota updated

### How WhatsApp Works with the Mobile App

The mobile app and WhatsApp are two separate apps on the same phone. They do NOT communicate directly:

```
┌─────────────────────────────────────────────────────┐
│                 Operator's Phone                     │
│                                                      │
│  ┌──────────┐              ┌──────────────────────┐ │
│  │ WhatsApp │              │  KopTumbuh Mobile    │ │
│  │ (Meta)   │              │  App (Flutter)       │ │
│  │          │              │                      │ │
│  │ Used to: │              │  Used to:            │ │
│  │ • Send   │              │  • View transactions │ │
│  │   trans- │              │  • Check stock       │ │
│  │   action │              │  • See recommend-    │ │
│  │   msgs   │              │    ations            │ │
│  │ • Reply  │              │  • Manual entry      │ │
│  │   YA/    │              │  • Record savings    │ │
│  │   UBAH   │              │  • Record restock    │ │
│  └────┬─────┘              └──────────┬───────────┘ │
│       │                               │             │
└───────┼───────────────────────────────┼─────────────┘
        │                               │
        │ Evolution API                 │ REST API
        ▼                               ▼
┌─────────────────────────────────────────────────────┐
│                   Backend API                        │
└─────────────────────────────────────────────────────┘
```

**What the mobile app does NOT do:**
- It does NOT send or receive WhatsApp messages directly
- It does NOT have a chat interface
- It does NOT handle the YA/UBAH/BATAL confirmation (that happens in WhatsApp)
- It does NOT do AI processing (backend handles all AI)

**What the mobile app DOES:**
- Read-only view of WhatsApp message history and parsing results
- Manual transaction/restock/savings entry (form-based, not chat)
- Inventory browsing with stock level indicators
- Recommendation feed with action buttons
- Member search and detail view
- Dashboard summary KPIs

### Mobile App Architecture (Flutter)

```
lib/
├── main.dart
├── app.dart                        # MaterialApp, theme, routing
├── config/
│   └── api_config.dart             # Base URL, token storage key
├── models/                         # Data classes matching API responses
│   ├── transaction.dart
│   ├── product.dart
│   ├── member.dart
│   ├── recommendation.dart
│   ├── message.dart
│   └── user.dart
├── services/
│   ├── api_client.dart             # HTTP client with JWT auth + auto-refresh
│   ├── auth_service.dart           # Login, logout, token persistence
│   ├── polling_service.dart        # 10-second poll for new messages
│   └── notification_service.dart   # Local push when confirmation ready
├── providers/                      # State management (Riverpod or Provider)
│   ├── auth_provider.dart
│   ├── dashboard_provider.dart
│   ├── transaction_provider.dart
│   ├── product_provider.dart
│   ├── recommendation_provider.dart
│   └── message_provider.dart
├── screens/
│   ├── login_screen.dart
│   ├── home_screen.dart            # Bottom nav shell
│   ├── dashboard/
│   │   └── dashboard_screen.dart   # KPI cards + recent activity
│   ├── transactions/
│   │   ├── transaction_list_screen.dart
│   │   ├── transaction_detail_screen.dart
│   │   └── manual_entry_screen.dart
│   ├── products/
│   │   ├── product_list_screen.dart
│   │   ├── product_detail_screen.dart
│   │   └── restock_screen.dart
│   ├── recommendations/
│   │   └── recommendation_list_screen.dart
│   ├── members/
│   │   ├── member_search_screen.dart
│   │   └── member_detail_screen.dart
│   ├── messages/
│   │   ├── message_list_screen.dart
│   │   └── message_detail_screen.dart
│   └── profile/
│       └── profile_screen.dart
├── widgets/                        # Reusable UI components
│   ├── kpi_card.dart
│   ├── stock_badge.dart
│   ├── priority_badge.dart
│   ├── transaction_list_tile.dart
│   ├── product_list_tile.dart
│   └── recommendation_card.dart
└── utils/
    ├── currency_format.dart        # Rp formatting
    ├── date_format.dart            # Indonesian date formatting
    └── validators.dart
```

### Mobile-Specific Technical Decisions

| Concern | Choice | Why |
|---------|--------|-----|
| **Framework** | Flutter 3.x | Single codebase for Android + iOS, the user is already using it |
| **State management** | Riverpod | Compile-safe, testable, good for REST-heavy apps |
| **HTTP client** | Dio | Interceptors for JWT refresh, retry, logging |
| **Local storage** | flutter_secure_storage | JWT tokens, user preferences |
| **Polling** | Timer.periodic (10s) | Simple, no WebSocket infrastructure needed |
| **Background refresh** | workmanager | Check for new recommendations while app is backgrounded |
| **Local notifications** | flutter_local_notifications | Notify operator when AI finishes processing a message |
| **API base URL** | Configurable | Dev: `http://10.0.2.2:8000/api/v1` (Android emulator), Prod: real URL |

### Mobile Polling & Real-Time Strategy

The mobile app polls these endpoints on a timer:

| Poll Interval | Endpoint | Purpose |
|--------------|----------|---------|
| Every 10 seconds | `GET /mobile/messages?status=PARSED&since={last_check}` | Check for new AI-parsed messages needing attention |
| Every 30 seconds | `GET /mobile/dashboard/summary` | Refresh KPI numbers |
| Every 60 seconds | `GET /mobile/recommendations?status=NEW` | Check for new AI recommendations |
| On screen focus | `GET /mobile/products` | Refresh stock levels when user navigates to Products tab |

When a new `PARSED` message appears (meaning AI is done and confirmation was sent to the operator's WhatsApp), the mobile app shows a local notification: *"Konfirmasi transaksi siap — cek WhatsApp Anda."*

When a new `CONFIRMED` message appears (transaction committed), the mobile app refreshes the transaction list and dashboard KPIs.

### Mobile App MVP Feature Checklist

**Phase 1 (Hackathon MVP):**
- [ ] Login with phone + password → JWT
- [ ] Dashboard: KPI cards (today's sales, tx count, alerts, pending recs)
- [ ] Transaction list: paginated, with date filter
- [ ] Transaction detail: line items, customer, payment method
- [ ] Manual transaction entry form
- [ ] Product list with stock levels and ⚠️ indicators
- [ ] Product detail with stock history
- [ ] Restock recording form
- [ ] Recommendation list with priority badges
- [ ] Mark recommendation as READ/ACCEPTED/REJECTED
- [ ] Message history (read-only view of WhatsApp messages)
- [ ] Message detail with AI parsing result
- [ ] Member search (Operator/Admin only)
- [ ] Member detail with savings (Operator/Admin only)
- [ ] Member savings recording form (Operator only)
- [ ] Profile screen (all roles — anggota sees own savings + transaction history)
- [ ] My Transactions (Anggota only — own purchase history)
- [ ] My Savings (Anggota only — own savings balance & deposit history)
- [ ] Auto-refresh via polling
- [ ] Local notification when confirmation is ready
- [ ] **Offline queue** — queue TX messages locally when no internet, sync when back online

#### Offline Queue Strategy

Many village cooperatives have intermittent internet. If WhatsApp message isn't delivered, no transaction is recorded — operator goes back to paper.

**How it works in the mobile app:**
1. Operator opens KopTumbuh app → taps "Rekam Offline"
2. Fills form: customer, products, quantities, payment method (same as manual entry)
3. App stores transaction in local SQLite queue with timestamp
4. When internet returns, app syncs: POSTs each queued TX to `/mobile/transactions` with original timestamp
5. Backend accepts `tanggal_dibuat` from the past (offline timestamps are authoritative)
6. Confirmation sent to operator's WhatsApp when sync completes

**What changes:**
- Mobile app: `sqflite` package for local queue storage
- Backend: `POST /mobile/transactions` accepts optional `tanggal_dibuat` parameter
- No changes to WhatsApp flow — offline entry is manual (form-based), not WhatsApp

**Post-MVP:**
- [ ] Customer (walk-in) CRUD
- [ ] Supplier list and detail
- [ ] Barcode scanner for product lookup
- [ ] Push notifications via FCM instead of polling
- [ ] Dark mode
- [ ] Multi-language (Bahasa Indonesia / English)

---

---

## Koptumbuh Core Engines — The Background Processing Layer

Five engines run as Celery tasks behind the API. They are the "brain" of KopTumbuh — the web dashboard and mobile app only display their output.

```
┌─────────────────────────────────────────────────────────────────┐
│                    KOPTUMBUH CORE ENGINES                        │
│              (Celery workers + Celery Beat scheduler)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ 1. TRANSACTION  │  │ 2. VALIDATION   │  │ 3. SUPPLY CHAIN │  │
│  │    ENGINE       │  │    ENGINE       │  │    ENGINE       │  │
│  │                 │  │                 │  │                 │  │
│  │ • Message       │  │ • Entity        │  │ • Stockout risk │  │
│  │   routing       │  │   resolution    │  │   prediction    │  │
│  │   (text/audio/  │  │   (fuzzy match) │  │ • Days-remaining│  │
│  │   image)        │  │ • Price lookup  │  │   calculation   │  │
│  │ • Gemini        │  │   (DB source)   │  │ • Lead time     │  │
│  │   extraction    │  │ • Deterministic │  │   factoring     │  │
│  │ • Audio → text  │  │   math engine   │  │ • Restock qty   │  │
│  │ • Image → JSON  │  │ • AI total      │  │   suggestion    │  │
│  │                 │  │   DISCARDED     │  │ • Slow-moving   │  │
│  │                 │  │                 │  │   detection     │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │            │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐  │
│  │ 4. RECOMMENDER  │  │ 5. EXPORT &     │  │ 6. STOCK        │  │
│  │    ENGINE       │  │    INTEGRATION  │  │    RECONCILIATION│  │
│  │                 │  │    ENGINE       │  │    ENGINE       │  │
│  │ • STOCKOUT_RISK │  │                 │  │                 │  │
│  │ • SLOW_MOVING   │  │ • SIMKOPDES     │  │ • Movement-based│  │
│  │ • RESTOCK       │  │   field mapping │  │   stock calc    │  │
│  │ • BUNDLING      │  │ • CSV/XLSX/JSON │  │ • Snapshot      │  │
│  │ • PROMOTION     │  │   generation    │  │   comparison    │  │
│  │ • Deduplication │  │ • MinIO upload  │  │ • Mismatch flag │  │
│  │ • Priority      │  │ • mapping_      │  │ • Adjustment    │  │
│  │   assignment    │  │   integrasi     │  │   audit         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 7. BUSINESS INTELLIGENCE    │ 8. RELATIONSHIP MGMT         │  │
│  │    ENGINE (PostgreSQL views)│    ENGINE (PostgreSQL views)  │  │
│  │                             │                               │  │
│  │ • Omzet & transaksi         │ • RFM segmentation            │  │
│  │ • Top products              │   (DIAMOND→TIDAK_AKTIF)      │  │
│  │ • Profit margins            │ • Retention status            │  │
│  │ • Slow-moving detection     │ • Per-member product          │  │
│  │ • Active member ranking     │   preferences & favorites     │  │
│  └─────────────────────────────┴──────────────────────────────┘  │
│                                                                  │
│  SCHEDULE:                                                       │
│  • Recommender: every 4 hours (Celery Beat cron)                 │
│  • Export: on-demand (user triggered)                            │
│  • Transaction: on-demand (webhook triggered)                    │
│  • BI & Relationship: real-time (PostgreSQL views)               │
│  • Reconciliation: real-time (v_rekonsiliasi_stok view)          │
└─────────────────────────────────────────────────────────────────┘
```

### Engine 1: Transaction Engine

| Worker | Trigger | Input | Output |
|--------|---------|-------|--------|
| `process_message` | WhatsApp webhook | Message (text/audio/image) | `parsing_pesan` record with extracted entities |
| `parse_text` | Chained from router | Raw text (Indonesian) | Structured JSON via Gemini 2.5 Flash |
| `transcribe_audio` | Chained from router | Audio bytes (OGG) | Indonesian text via Gemini audio |
| `ocr_receipt` | Chained from router | Image bytes (JPEG/PNG) | Structured JSON via Gemini multimodal |

### Engine 2: Validation Engine

| Worker | Trigger | What It Does | "No AI Math" Enforcement |
|--------|---------|-------------|--------------------------|
| `validate_parsing` | Chained from Transaction Engine | Entity resolution + price lookup + math | **Discards ANY AI-computed total.** Looks up `harga_jual` from `produk_koperasi` via PostgreSQL. Calculates `quantity × db_price` server-side. |

**Entity resolution pipeline:**
1. Exact match on `nama_produk`
2. `ILIKE '%keyword%'` (case-insensitive substring)
3. Word-overlap / Jaccard similarity on tokenized names
4. If no match → flag `NEEDS_REVIEW`, send error to user with closest suggestions

#### Credit/Hutang Transaction Support

70%+ of rural cooperative sales are on credit — members pay at harvest time. Without this, operators won't adopt.

**WhatsApp flow:** "Bu Siti beli 2 Beras 5kg, bayar nanti, jatuh tempo 15 Agustus"

Gemini extracts `payment_method = 'Hutang'`. Confirmation shows:
```
📋 *Konfirmasi (HUTANG)*  Total: Rp 130.000  Jatuh Tempo: 15 Agustus 2026
YA / UBAH / BATAL
```

**DB changes on YA:** `transaksi_penjualan.status_transaksi = 'Unpaid'`, `metode_pembayaran = 'Hutang'`. Inventory still decremented. Auto piutang tracking:

```sql
CREATE OR REPLACE VIEW koptumbuh.v_piutang_anggota AS
SELECT r.anggota_ref, a.nama, t.koperasi_ref,
    COUNT(*) AS jumlah_hutang, SUM(t.total_pembayaran) AS total_piutang,
    MIN(t.tanggal_dibuat) AS hutang_terlama
FROM transaksi_penjualan t
JOIN relasi_transaksi_pihak r ON r.transaksi_sample_id = t.transaksi_sample_id
JOIN anggota_koperasi a ON a.anggota_ref = r.anggota_ref
WHERE t.status_transaksi = 'Unpaid' AND t.metode_pembayaran = 'Hutang'
GROUP BY r.anggota_ref, a.nama, t.koperasi_ref;
```

**Payment settlement:** Operator replies `LUNAS` to credit reminder → `UPDATE SET status_transaksi = 'Paid'`.

### Engine 3: Supply Chain Engine

| Worker | Schedule | What It Calculates |
|--------|----------|--------------------|
| `generate_for_cooperative` | Every 4 hours (Celery Beat) | For every product: `avg_daily_sales = total_sold_14d / 14`, `days_remaining = current_stock / ads`, `threshold = ads × (lead_time + 2)`. If `days_remaining ≤ threshold` → STOCKOUT_RISK alert. |

**Stockout risk formula:**
```
ADS (Average Daily Sales) = Total Quantity Sold in 14 Days / 14
Days Remaining = Current Stock / ADS
Threshold = Supplier Lead Time (days) + 2 Safety Days

If Days Remaining ≤ Threshold → Generate STOCKOUT_RISK recommendation
Suggested Order Qty = (Threshold × ADS) - Current Stock
```

**Slow-moving detection:** Products with stock > 0 and zero sales in 14+ days → SLOW_MOVING flag.

#### Price Change Alert

When a new `barang_masuk` record has `harga_beli` higher than the previous purchase, alert the operator before margin silently erodes:

```sql
-- v_harga_berubah: Detect price changes per product
CREATE OR REPLACE VIEW koptumbuh.v_harga_berubah AS
WITH latest_price AS (
    SELECT DISTINCT ON (produk_sample_id, koperasi_ref)
        produk_sample_id, koperasi_ref, harga_beli, harga_jual, tanggal_masuk
    FROM barang_masuk_produk
    WHERE COALESCE(status,'') NOT IN ('Rejected','Cancelled')
    ORDER BY produk_sample_id, koperasi_ref, tanggal_masuk DESC
),
previous_price AS (
    SELECT DISTINCT ON (produk_sample_id, koperasi_ref)
        produk_sample_id, koperasi_ref, harga_beli AS prev_beli, harga_jual AS prev_jual
    FROM barang_masuk_produk
    WHERE COALESCE(status,'') NOT IN ('Rejected','Cancelled')
    ORDER BY produk_sample_id, koperasi_ref, tanggal_masuk DESC
    OFFSET 1  -- second most recent
)
SELECT p.nama_produk, l.koperasi_ref,
    l.harga_beli, pp.prev_beli,
    ROUND(((l.harga_beli - pp.prev_beli) / pp.prev_beli * 100)::numeric, 1) AS kenaikan_persen,
    l.harga_jual, pp.prev_jual,
    CASE WHEN l.harga_jual <= pp.prev_jual THEN TRUE ELSE FALSE END AS perlu_naikkan_jual
FROM latest_price l
JOIN produk_koperasi p ON p.produk_sample_id = l.produk_sample_id
JOIN previous_price pp ON pp.produk_sample_id = l.produk_sample_id
WHERE l.harga_beli > pp.prev_beli;
```

When `kenaikan_persen > 5` AND `perlu_naikkan_jual = TRUE`, generate a WhatsApp alert: "Harga beli Beras Premium 5kg naik 8% (Rp 55.000 → Rp 59.500). Harga jual masih Rp 65.000. Pertimbangkan naikkan ke Rp 70.000."

#### Safety Stock & Auto-Reorder

Static reorder points fail when demand varies. Safety stock accounts for demand volatility:

```
safety_stock = (max_daily_sales_last_30d - avg_daily_sales_last_30d) × lead_time_days
reorder_point = (avg_daily_sales × lead_time_days) + safety_stock
```

When `current_stock ≤ reorder_point`, the system auto-generates a draft `purchase_order`:

```python
@celery_app.task
def auto_generate_po(koperasi_ref: str):
    """Check all products — if below reorder point, create draft PO linked to supplier."""
    products = get_products_below_reorder(koperasi_ref)
    for p in products:
        supplier = get_primary_supplier(koperasi_ref, p.produk_sample_id)
        if not supplier:
            continue

        suggested_qty = (p.threshold * p.ads) - p.current_stock
        # Round up to nearest supplier pack size
        if hasattr(supplier, 'min_order_qty') and supplier.min_order_qty:
            suggested_qty = max(suggested_qty, supplier.min_order_qty)

        po = PurchaseOrder(
            koperasi_ref=koperasi_ref,
            pemasok_id=supplier.pemasok_id,
            status='DRAFT',
            tanggal_order=date.today(),
            tanggal_estimasi=date.today() + timedelta(days=supplier.lead_time_hari)
        )
        db.add(po)
        db.flush()

        item = PurchaseOrderItem(
            po_id=po.po_id,
            produk_sample_id=p.produk_sample_id,
            jumlah_dipesan=suggested_qty,
            harga_per_unit=p.latest_harga_beli
        )
        db.add(item)

    db.commit()
    # WhatsApp: "3 draft PO siap ditinjau. Buka dashboard untuk review."
```

**Safety stock view:**

```sql
CREATE OR REPLACE VIEW koptumbuh.v_safety_stock AS
WITH daily_stats AS (
    SELECT produk_sample_id, koperasi_ref,
        AVG(jumlah_keluar) AS avg_daily,
        MAX(jumlah_keluar) AS max_daily
    FROM barang_keluar_produk
    WHERE tanggal_keluar >= CURRENT_DATE - INTERVAL '30 days'
      AND COALESCE(status_transaksi,'') NOT IN ('Refund','Cancelled')
    GROUP BY produk_sample_id, koperasi_ref
)
SELECT p.produk_sample_id, p.nama_produk, i.stok,
    ds.avg_daily, ds.max_daily, s.lead_time_hari,
    ROUND((ds.max_daily - ds.avg_daily) * COALESCE(s.lead_time_hari, 3)) AS safety_stock,
    ROUND(ds.avg_daily * COALESCE(s.lead_time_hari, 3) +
          (ds.max_daily - ds.avg_daily) * COALESCE(s.lead_time_hari, 3)) AS reorder_point,
    CASE WHEN i.stok <= ROUND(ds.avg_daily * COALESCE(s.lead_time_hari, 3) +
          (ds.max_daily - ds.avg_daily) * COALESCE(s.lead_time_hari, 3))
         THEN TRUE ELSE FALSE END AS perlu_reorder
FROM produk_koperasi p
JOIN inventaris_produk i ON i.produk_sample_id = p.produk_sample_id
JOIN daily_stats ds ON ds.produk_sample_id = p.produk_sample_id
LEFT JOIN LATERAL (
    SELECT pemasok_id, lead_time_hari FROM pemasok_koptumbuh
    WHERE koperasi_ref = p.koperasi_ref LIMIT 1
) s ON TRUE;
```

#### Partial Delivery Handling

When receiving goods against a PO, the operator records what ACTUALLY arrived. The system compares against what was ordered:

```python
@app.post("/admin/purchase-orders/{po_id}/receive")
async def receive_po_items(po_id: str, received_items: list[dict]):
    """Record goods received against a PO. Handle partial delivery."""
    po = get_po(po_id)

    for item in received_items:
        po_item = get_po_item(po_id, item['produk_sample_id'])
        po_item.jumlah_diterima += item['jumlah_diterima']

        # Create barang_masuk record
        barang_masuk = BarangMasukProduk(
            koperasi_ref=po.koperasi_ref,
            produk_sample_id=item['produk_sample_id'],
            jumlah_masuk=item['jumlah_diterima'],
            harga_beli=po_item.harga_per_unit,
            status='Diterima',
            sumber=f'PO-{po_id}'
        )
        db.add(barang_masuk)

    # Update PO status
    all_received = all(pi.jumlah_diterima >= pi.jumlah_dipesan for pi in po.items)
    any_received = any(pi.jumlah_diterima > 0 for pi in po.items)

    if all_received:
        po.status = 'DITERIMA'
    elif any_received:
        po.status = 'DITERIMA_SEBAGIAN'
        # Alert: remaining items pending
        pending = [pi for pi in po.items if pi.jumlah_diterima < pi.jumlah_dipesan]
        # WhatsApp: "PO #123: 80/100 Beras diterima. 20 unit masih menunggu."
    db.commit()
```

#### Warehouse Location Tracking

Simple storage location per inventory item:

```sql
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS lokasi_simpan TEXT;
ALTER TABLE koptumbuh.inventaris_produk ADD COLUMN IF NOT EXISTS tanggal_masuk_gudang TIMESTAMPTZ;
```

Dashboard: `/inventory/locations` — grid view of warehouse layout. Admin Gudang assigns locations on receiving. Picking list shows location for dispatch.

#### Supply Chain Dashboard Widgets

| Widget | Data Source | What Operator Sees |
|--------|------------|-------------------|
| **Restock Checklist** | Auto-generated draft POs | "3 PO siap ditinjau. [Review]" |
| **Pending Deliveries** | PO with DITERIMA_SEBAGIAN | "2 pengiriman sebagian. Beras (20 unit tersisa), Minyak (15 unit tersisa)" |
| **Supplier Alert** | v_skor_pemasok with low on-time % | "⚠️ Supplier A: 60% tepat waktu bulan ini. Pertimbangkan alternatif." |
| **Stock Health** | v_safety_stock | "5 produk di bawah reorder point. 2 dalam status kritis (< 3 hari)." |

### Engine 4: Recommender Engine

| Recommendation Type | Trigger Condition | Priority | Action for Operator |
|---------------------|-------------------|----------|---------------------|
| **STOCKOUT_RISK** | `days_remaining ≤ lead_time + 2` | HIGH if ≤ 3 days, else MEDIUM | Order from supplier |
| **SLOW_MOVING** | No sales in 14 days, stock > 0 | LOW | Consider promotion or bundling |
| **RESTOCK** | Stock below reorder point | MEDIUM | Place purchase order |
| **BUNDLING** | Products frequently bought together (simple correlation) | MEDIUM | Create bundle promo |
| **PROMOTION** | Slow-moving items with high margin | LOW | Run discount campaign |

**Deduplication:** Before generating, check existing `NEW`/`READ` recommendations in last 24h for same `(produk_sample_id, jenis)` pair. Skip if already exists.

#### Bundle Deal Auto-Generator

Products frequently bought together → auto-generate bundle with discount:

```sql
-- v_bundle_suggestions: Product pairs bought together
CREATE OR REPLACE VIEW koptumbuh.v_bundle_suggestions AS
WITH pairs AS (
    SELECT
        a.produk_sample_id AS produk_a,
        b.produk_sample_id AS produk_b,
        a.koperasi_ref,
        COUNT(DISTINCT a.transaksi_sample_id) AS dibeli_bersama,
        SUM(a.total_nilai + b.total_nilai) AS total_nilai_bundle
    FROM barang_keluar_produk a
    JOIN barang_keluar_produk b
        ON a.transaksi_sample_id = b.transaksi_sample_id
        AND a.produk_sample_id < b.produk_sample_id
    WHERE COALESCE(a.status_transaksi,'') NOT IN ('Refund','Cancelled')
      AND COALESCE(b.status_transaksi,'') NOT IN ('Refund','Cancelled')
    GROUP BY a.produk_sample_id, b.produk_sample_id, a.koperasi_ref
    HAVING COUNT(DISTINCT a.transaksi_sample_id) >= 3
)
SELECT p.koperasi_ref, p.produk_a, p.produk_b,
    pa.nama_produk AS nama_a, pb.nama_produk AS nama_b,
    p.dibeli_bersama,
    ma.harga_jual AS harga_a, mb.harga_jual AS harga_b,
    (ma.harga_jual + mb.harga_jual) AS harga_normal,
    ROUND((ma.harga_jual + mb.harga_jual) * 0.93) AS harga_bundle,
    ROUND((ma.harga_jual + mb.harga_jual) * 0.07) AS hemat
FROM pairs p
JOIN produk_koperasi pa ON pa.produk_sample_id = p.produk_a
JOIN produk_koperasi pb ON pb.produk_sample_id = p.produk_b
JOIN LATERAL (SELECT harga_jual FROM barang_masuk_produk
    WHERE produk_sample_id = p.produk_a ORDER BY tanggal_masuk DESC LIMIT 1) ma ON TRUE
JOIN LATERAL (SELECT harga_jual FROM barang_masuk_produk
    WHERE produk_sample_id = p.produk_b ORDER BY tanggal_masuk DESC LIMIT 1) mb ON TRUE
ORDER BY p.dibeli_bersama DESC;
```

Bundle appears in WhatsApp daily broadcast: "📦 Paket Hemat: Beras 5kg + Minyak 2L = Rp 93.000 (hemat Rp 7.000)."

#### Morning Price Broadcast (Daily, 7 AM)

Celery Beat triggers at 7 AM daily. Pulls `v_perbandingan_harga` — sends WhatsApp broadcast to all registered member numbers:

```
📋 *Harga Hari Ini — 11 Juli 2026*

🟢 Beras Premium 5kg   Rp 65.000  (10% < pasar)
🟢 Minyak Goreng 2L    Rp 28.000  (3% < pasar)
🟡 Telur Ayam 1kg      Rp 27.000  (harga pasar)

📦 Paket Hemat: Beras + Minyak = Rp 93.000 (hemat Rp 7.000)
💡 Bayar pakai Simpanan? Lebih mudah, tanpa uang tunai.

_Balas PESAN [produk] untuk pre-order_
```

This single automation drives the highest volume impact — every member sees prices every morning without visiting the store.

#### SHU Personal Projection

Member sends WhatsApp query: "SHU saya?" → backend calculates from their spending history:

```sql
-- Per-member SHU projection (simplified)
SELECT a.anggota_ref, a.nama,
    COALESCE(SUM(t.total_pembayaran), 0) AS total_belanja_tahun_ini,
    ROUND(COALESCE(SUM(t.total_pembayaran), 0) * 0.05) AS estimasi_shu,
    COUNT(DISTINCT t.transaksi_sample_id) AS jumlah_transaksi
FROM anggota_koperasi a
LEFT JOIN relasi_transaksi_pihak r ON r.anggota_ref = a.anggota_ref
LEFT JOIN transaksi_penjualan t ON t.transaksi_sample_id = r.transaksi_sample_id
    AND EXTRACT(YEAR FROM t.tanggal_dibuat) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND COALESCE(t.status_transaksi,'') NOT IN ('Refund','Cancelled')
WHERE a.anggota_ref = :query_anggota_ref
GROUP BY a.anggota_ref, a.nama;
```

WhatsApp response: "Total belanja Anda tahun ini: Rp 3.450.000. Estimasi SHU: Rp 172.500. Semakin banyak belanja, semakin besar SHU Anda."

#### Daily Operator "What to Push" Dashboard Widget

Every morning at POS login, the operator sees:

```
┌─────────────────────────────────────────────┐
│  ☀️ Selamat Pagi, Budi!                       │
│                                              │
│  Hari ini, fokus jual:                       │
│  🥇 Beras Premium 5kg — margin tertinggi     │
│  🥈 Paket Hemat Beras+Minyak — best seller   │
│  🥉 Telur Ayam 1kg — stok harus habis hari ini│
│                                              │
│  ⚠️ Perhatian:                                │
│  • 3 anggota belum bayar hutang              │
│  • Stok Telur tinggal 3 kg (expiring soon)   │
│  • Bu Siti sudah 30 hari tidak belanja       │
└─────────────────────────────────────────────┘
```

#### Expiring Stock Alert

If `barang_masuk` has a `tanggal_masuk` older than 14 days and stock > 0 for perishables (Telur, Sayur), auto-generate PROMOTION recommendation: "Telur Ayam 1kg masuk 14 hari lalu, stok 3 kg. Diskon 10% untuk penjualan hari ini."

```sql
CREATE OR REPLACE VIEW koptumbuh.v_stok_expiring AS
SELECT p.produk_sample_id, p.nama_produk, i.stok,
    MAX(bm.tanggal_masuk) AS masuk_terakhir,
    (CURRENT_DATE - MAX(bm.tanggal_masuk)::date) AS hari_sejak_masuk,
    CASE WHEN (CURRENT_DATE - MAX(bm.tanggal_masuk)::date) >= 14 THEN TRUE ELSE FALSE END AS perlu_diskon
FROM produk_koperasi p
JOIN inventaris_produk i ON i.produk_sample_id = p.produk_sample_id
JOIN barang_masuk_produk bm ON bm.produk_sample_id = p.produk_sample_id
WHERE i.stok > 0 AND p.unit IN ('Kg', 'Liter', 'Butir')
GROUP BY p.produk_sample_id, p.nama_produk, i.stok;
```

### Engine 5: Export & Integration Engine

| Worker | Trigger | Output |
|--------|---------|--------|
| `generate_simkopdes_export` | User POSTs to `/admin/export/simkopdes` | CSV / XLSX / JSON file → MinIO → `ekspor_log` updated |

**Mapping flow:** Query local data → `mapping_integrasi` table translates local IDs to SIMKOPDES external references → generate file → upload → update `mapping_integrasi.mapping_status` to `EXPORTED`.

### Engine 6: Stock Reconciliation Engine

| Mechanism | How It Works |
|-----------|-------------|
| `v_stok_terhitung` (view) | Calculates `SUM(barang_masuk) - SUM(barang_keluar) + SUM(penyesuaian_stok)` per product |
| `v_rekonsiliasi_stok` (view) | Compares `v_stok_terhitung` against `inventaris_produk.stok` snapshot. Flags MATCH / MISMATCH / SNAPSHOT_MISSING. |
| `penyesuaian_stok` (table) | Manual adjustments with `pengguna_id` and `source_message_id` audit trail. Triggered by operator via mobile app or dashboard. |

**Reconciliation is real-time** — the views query live data, no scheduled job needed. Mismatches appear in the dashboard immediately when they occur.

#### Physical Stock Count Reminder

After prolonged WhatsApp-only recording, computed stock drifts from physical reality (theft, damage, counting errors). The system prompts for physical verification:

- Celery Beat: every 7 days, check if any product has had 50+ TX since last adjustment
- If yes → WhatsApp: "Sudah 7 hari sejak stok opname terakhir. 43 transaksi tercatat. Lakukan penghitungan fisik? Balas OPNAME"
- Operator counts physical stock, replies `OPNAME Beras 38` (actual = 38, computed = 43)
- System creates `penyesuaian_stok` record: `quantity_delta = -5`, `reason = 'Stok opname mingguan'`
- Reconciliation view now shows MATCH

This closes the loop between digital records and physical reality. Without it, inventory accuracy degrades over time.

### Engine 7: Business Intelligence Engine

The BI engine transforms raw transaction data into actionable metrics. Unlike the other engines, BI is powered by **PostgreSQL views** (real-time, no Celery job) and surfaced through the API.

| BI Metric | Source | What It Shows |
|-----------|--------|---------------|
| **Omzet & Jumlah Transaksi** | `v_penjualan_harian` | Daily revenue (omzet), transaction count, average basket size per cooperative |
| **Produk Terlaris** | `v_produk_terlaris` | Top products by quantity sold and revenue. Answers: "What's selling fastest?" |
| **Margin Produk** | `v_margin_produk` ★ NEW | Per-product profit margin: `harga_jual - harga_beli`, margin %, total profit contributed |
| **Produk Lambat Bergerak** | `v_produk_lambat_bergerak` ★ NEW | Products with stock > 0 and zero sales in 14 days. Days since last sale. Ties into SLOW_MOVING recommendations. |
| **Anggota Aktif** | `v_anggota_aktif` ★ NEW | Member ranking by: transaction count, total spending, last transaction date. Flags inactive members (>30 days no activity). |
| **Insight & Rekomendasi** | Recommender Engine (Engine 4) | AI-generated: STOCKOUT_RISK, SLOW_MOVING, RESTOCK, BUNDLING, PROMOTION. Priority-ranked, deduplicated. |

**Three new views to add** (migration — additive, does not modify canonical schema):

```sql
-- v_margin_produk: Profit margin per product
CREATE OR REPLACE VIEW koptumbuh.v_margin_produk AS
SELECT
    p.koperasi_ref,
    p.produk_sample_id,
    p.nama_produk,
    latest_bm.harga_beli,
    latest_bm.harga_jual,
    (latest_bm.harga_jual - latest_bm.harga_beli) AS margin_nominal,
    CASE WHEN latest_bm.harga_beli > 0
         THEN ROUND(((latest_bm.harga_jual - latest_bm.harga_beli) / latest_bm.harga_beli * 100)::numeric, 1)
         ELSE 0 END AS margin_persen,
    COALESCE(sales.total_terjual, 0) AS total_terjual,
    (latest_bm.harga_jual - latest_bm.harga_beli) * COALESCE(sales.total_terjual, 0) AS total_profit
FROM koptumbuh.produk_koperasi p
LEFT JOIN LATERAL (
    SELECT harga_beli, harga_jual
    FROM koptumbuh.barang_masuk_produk
    WHERE produk_sample_id = p.produk_sample_id
      AND koperasi_ref = p.koperasi_ref
      AND COALESCE(status, '') NOT IN ('Rejected', 'Cancelled')
    ORDER BY tanggal_masuk DESC LIMIT 1
) latest_bm ON TRUE
LEFT JOIN (
    SELECT produk_sample_id, koperasi_ref, SUM(jumlah_keluar) AS total_terjual
    FROM koptumbuh.barang_keluar_produk
    WHERE COALESCE(status_transaksi, '') NOT IN ('Refund', 'Cancelled')
    GROUP BY produk_sample_id, koperasi_ref
) sales ON sales.produk_sample_id = p.produk_sample_id AND sales.koperasi_ref = p.koperasi_ref;

-- v_produk_lambat_bergerak: Slow-moving products
CREATE OR REPLACE VIEW koptumbuh.v_produk_lambat_bergerak AS
SELECT
    p.koperasi_ref,
    p.produk_sample_id,
    p.nama_produk,
    i.stok AS stok_saat_ini,
    latest_sale.terakhir_terjual,
    CASE WHEN latest_sale.terakhir_terjual IS NOT NULL
         THEN (CURRENT_DATE - latest_sale.terakhir_terjual::date)
         ELSE 999 END AS hari_tanpa_penjualan,
    CASE WHEN latest_sale.terakhir_terjual IS NULL THEN 'BELUM_PERNAH_TERJUAL'
         WHEN (CURRENT_DATE - latest_sale.terakhir_terjual::date) >= 30 THEN '30_LEBIH_HARI'
         WHEN (CURRENT_DATE - latest_sale.terakhir_terjual::date) >= 14 THEN '14_30_HARI'
         ELSE 'AKTIF' END AS status_pergerakan
FROM koptumbuh.produk_koperasi p
JOIN koptumbuh.inventaris_produk i
    ON i.produk_sample_id = p.produk_sample_id AND i.koperasi_ref = p.koperasi_ref
LEFT JOIN LATERAL (
    SELECT MAX(tanggal_keluar) AS terakhir_terjual
    FROM koptumbuh.barang_keluar_produk
    WHERE produk_sample_id = p.produk_sample_id
      AND koperasi_ref = p.koperasi_ref
      AND COALESCE(status_transaksi, '') NOT IN ('Refund', 'Cancelled')
) latest_sale ON TRUE
WHERE i.stok > 0
  AND (latest_sale.terakhir_terjual IS NULL
       OR latest_sale.terakhir_terjual < CURRENT_DATE - INTERVAL '14 days');

-- v_anggota_aktif: Active member ranking
CREATE OR REPLACE VIEW koptumbuh.v_anggota_aktif AS
SELECT
    a.koperasi_ref,
    a.anggota_ref,
    a.nama,
    a.status_keanggotaan,
    a.tanggal_terdaftar,
    COUNT(DISTINCT r.transaksi_sample_id) AS jumlah_transaksi,
    COALESCE(SUM(t.total_pembayaran), 0) AS total_belanja,
    MAX(t.tanggal_dibuat) AS transaksi_terakhir,
    CASE WHEN MAX(t.tanggal_dibuat) IS NULL THEN 'TIDAK_AKTIF'
         WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '30 days' THEN 'TIDAK_AKTIF_30_HARI'
         WHEN MAX(t.tanggal_dibuat) < CURRENT_DATE - INTERVAL '7 days' THEN 'KURANG_AKTIF'
         ELSE 'AKTIF' END AS status_aktivitas
FROM koptumbuh.anggota_koperasi a
LEFT JOIN koptumbuh.relasi_transaksi_pihak r
    ON r.anggota_ref = a.anggota_ref
LEFT JOIN koptumbuh.transaksi_penjualan t
    ON t.transaksi_sample_id = r.transaksi_sample_id
    AND COALESCE(t.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
GROUP BY a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan, a.tanggal_terdaftar;
```

**BI API endpoints** (added to `/admin/dashboard/`):

| Endpoint | View | Purpose |
|----------|------|---------|
| `GET /admin/dashboard/margin` | `v_margin_produk` | Profit margin per product — nominal + percentage |
| `GET /admin/dashboard/slow-moving` | `v_produk_lambat_bergerak` | Products not selling — days inactive, status |
| `GET /admin/dashboard/active-members` | `v_anggota_aktif` | Member ranking — spending, recency, activity status |

### Engine 8: Relationship Management Engine

Beyond tracking transactions, the cooperative needs to understand WHO its members are — their value, their habits, and their preferences. This engine powers targeted engagement.

| Feature | Source | What It Shows |
|---------|--------|---------------|
| **Segmentasi Anggota (RFM)** | `v_segmentasi_anggota` ★ NEW | Recency (days since last purchase), Frequency (transaction count), Monetary (total spending). Tiers: DIAMOND, EMAS, PERAK, PERUNGGU, TIDAK_AKTIF. |
| **Preferensi Produk** | `v_preferensi_anggota` ★ NEW | Per member: most purchased product categories, favorite products, average basket size, preferred payment method. |
| **Loyalitas & Frekuensi** | `v_anggota_aktif` (existing) | Transaction count, total spending, last active date. Tier assignment via RFM view. |

**Two new views:**

```sql
-- v_segmentasi_anggota: RFM segmentation
CREATE OR REPLACE VIEW koptumbuh.v_segmentasi_anggota AS
WITH rfm AS (
    SELECT
        a.koperasi_ref,
        a.anggota_ref,
        a.nama,
        a.status_keanggotaan,
        COUNT(DISTINCT r.transaksi_sample_id) AS frekuensi,
        COALESCE(SUM(t.total_pembayaran), 0) AS moneter,
        MAX(t.tanggal_dibuat) AS transaksi_terakhir,
        CASE WHEN MAX(t.tanggal_dibuat) IS NOT NULL
             THEN (CURRENT_DATE - MAX(t.tanggal_dibuat)::date)
             ELSE 999 END AS resensi_hari
    FROM koptumbuh.anggota_koperasi a
    LEFT JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref = a.anggota_ref
    LEFT JOIN koptumbuh.transaksi_penjualan t
        ON t.transaksi_sample_id = r.transaksi_sample_id
        AND COALESCE(t.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
    GROUP BY a.koperasi_ref, a.anggota_ref, a.nama, a.status_keanggotaan
)
SELECT
    *,
    CASE
        WHEN frekuensi >= 10 AND moneter >= 500000 THEN 'DIAMOND'
        WHEN frekuensi >= 5  AND moneter >= 250000 THEN 'EMAS'
        WHEN frekuensi >= 2  AND moneter >= 100000 THEN 'PERAK'
        WHEN frekuensi >= 1  THEN 'PERUNGGU'
        ELSE 'TIDAK_AKTIF'
    END AS segmentasi,
    CASE
        WHEN resensi_hari <= 7  AND frekuensi >= 5 THEN 'PELANGGAN_SETIA'
        WHEN resensi_hari <= 30 AND frekuensi >= 3 THEN 'PELANGGAN_REGULER'
        WHEN resensi_hari <= 60 THEN 'PELANGGAN_JARANG'
        WHEN resensi_hari <= 180 THEN 'RISIKO_HILANG'
        ELSE 'HILANG'
    END AS status_retensi
FROM rfm;

-- v_preferensi_anggota: Per-member product preferences
CREATE OR REPLACE VIEW koptumbuh.v_preferensi_anggota AS
SELECT
    a.koperasi_ref,
    a.anggota_ref,
    a.nama,
    bk.produk_sample_id,
    p.nama_produk,
    COUNT(*) AS kali_dibeli,
    SUM(bk.jumlah_keluar) AS total_qty,
    SUM(bk.total_nilai) AS total_spent,
    RANK() OVER (PARTITION BY a.anggota_ref ORDER BY COUNT(*) DESC) AS peringkat_preferensi
FROM koptumbuh.anggota_koperasi a
JOIN koptumbuh.relasi_transaksi_pihak r ON r.anggota_ref = a.anggota_ref
JOIN koptumbuh.barang_keluar_produk bk ON bk.transaksi_sample_id = r.transaksi_sample_id
JOIN koptumbuh.produk_koperasi p ON p.produk_sample_id = bk.produk_sample_id
WHERE COALESCE(bk.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
GROUP BY a.koperasi_ref, a.anggota_ref, a.nama, bk.produk_sample_id, p.nama_produk;
-- Top-ranked product (peringkat_preferensi = 1) = favorite product per member
```

**New BI API endpoints for Relationship Management:**

| Endpoint | View | Purpose |
|----------|------|---------|
| `GET /admin/dashboard/segmentation` | `v_segmentasi_anggota` | Member RFM tiers — DIAMOND through TIDAK_AKTIF |
| `GET /admin/dashboard/retention` | `v_segmentasi_anggota` | Retention status — PELANGGAN_SETIA through HILANG |
| `GET /admin/members/{id}/preferences` | `v_preferensi_anggota` | Per-member product preferences — top categories, favorite items |

#### Member Lifecycle Automation

CRM data (RFM, preferences, retention) already exists. These automations act on it.

**1. Win-Back Automation (Dormant → Active)**

When `status_retensi = 'HILANG'` (>180 days inactive), trigger a win-back sequence:

```
Day 0:   "Pak Haji, sudah 6 bulan tidak belanja di koperasi. Ada yang bisa kami bantu?"
Day 7:   (if no response) "Kabar baik! Diskon 10% untuk pembelian pertama Anda setelah kembali."
Day 14:  (if no response) "Kami rindu Anda, Pak Haji. Ada promo khusus: Beli 2 gratis 1 untuk produk pilihan."
Day 30:  (if no response) → mark as `ARCHIVED`. Stop messaging.
```

```python
@celery_app.task
def run_winback_campaign(koperasi_ref: str):
    dormant = get_members_by_retention(koperasi_ref, 'HILANG')
    for m in dormant:
        days_inactive = (date.today() - m.last_transaction).days
        stage = get_winback_stage(m.anggota_ref)

        match stage:
            case 0:
                send_whatsapp(m.phone, f"{m.nama}, sudah {days_inactive} hari tidak belanja. Ada yang bisa kami bantu?")
            case 1 if days_inactive >= 187:  # +7 days after first message
                send_whatsapp(m.phone, f"Diskon 10% untuk pembelian pertama Anda setelah kembali, {m.nama}!")
            case 2 if days_inactive >= 194:  # +14 days
                send_whatsapp(m.phone, f"Promo khusus: Beli 2 gratis 1 produk pilihan. Kunjungi koperasi hari ini!")
            case _ if days_inactive >= 210:  # +30 days
                archive_member(m.anggota_ref)

        advance_winback_stage(m.anggota_ref)
```

**2. New Member Onboarding (Auto-Welcome)**

Triggered when `status_keanggotaan = 'Approved'` and `tanggal_terdaftar = TODAY`:

```
Auto-send WhatsApp 1 hour after registration:
"Selamat bergabung di Koperasi Tumbuh Bersama, Bu Ani! 🎉

Cara belanja di koperasi kami:
1️⃣ WhatsApp: 'beli [produk] [jumlah]'
2️⃣ Bayar: Tunai atau Saldo Simpanan
3️⃣ Kumpulkan SHU: Semakin banyak belanja, semakin besar SHU Anda

Info simpanan Anda: Rp 50.000 (Simpanan Pokok)
Pertanyaan? Balas TANYA [pertanyaan Anda]"
```

**3. Member Milestone Recognition**

```python
@celery_app.task
def check_member_milestones(koperasi_ref: str):
    """Daily check for member milestones."""
    # First transaction ever
    first_timers = get_members_with_first_tx_today(koperasi_ref)
    for m in first_timers:
        send_whatsapp(m.phone, f"Terima kasih atas pembelian pertama Anda, {m.nama}! Selamat berbelanja di koperasi.")

    # Spending milestone (every Rp 1 juta)
    milestones = get_members_crossing_threshold(koperasi_ref, threshold=1_000_000)
    for m in milestones:
        send_whatsapp(m.phone,
            f"Selamat {m.nama}! Total belanja Anda sudah mencapai Rp {m.total_spent:,}. "
            f"Estimasi SHU Anda: Rp {m.estimated_shu:,}. Terus dukung koperasi kita!")
```

**4. Churn Risk Dashboard Widget**

```
┌─────────────────────────────────────────────┐
│  ⚠️ Risiko Kehilangan Anggota                │
│                                              │
│  HILANG (>180 hari)          12 anggota     │
│  RISIKO_HILANG (60-180 hari)  8 anggota     │
│  PELANGGAN_JARANG (30-60)     5 anggota     │
│                                              │
│  Win-back campaign aktif: 3 anggota          │
│  Win-back berhasil bulan ini: 2 anggota      │
│                                              │
│  [Jalankan Win-Back Campaign]               │
└─────────────────────────────────────────────┘
```

**Celery Beat schedule:**

```python
"member-milestone-check": {
    "task": "app.workers.relationship.check_member_milestones",
    "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM
},
"winback-campaign": {
    "task": "app.workers.relationship.run_winback_campaign",
    "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Every Monday 8 AM
},
"onboarding-check": {
    "task": "app.workers.relationship.send_onboarding_messages",
    "schedule": crontab(hour=9, minute=0),  # Daily at 9 AM
},
```

**Dashboard page:** `/members/churn-risk` — churn dashboard with win-back campaign status and success metrics.

### Engine 3 Enhancement: Supplier Scorecard & Purchase Orders

The Supply Chain Engine currently tracks lead time but lacks supplier performance analytics. Add these:

**Supplier Scorecard View:**

```sql
-- v_skor_pemasok: Supplier performance scorecard
CREATE OR REPLACE VIEW koptumbuh.v_skor_pemasok AS
WITH order_data AS (
    SELECT
        bm.pemasok_id,
        bm.produk_sample_id,
        bm.koperasi_ref,
        COUNT(*) AS total_pengiriman,
        AVG(EXTRACT(DAY FROM (bm.tanggal_masuk - bm.tanggal_dibuat))) AS rata_rata_lead_time_aktual,
        AVG(bm.harga_beli) AS rata_rata_harga,
        MIN(bm.harga_beli) AS harga_terendah,
        MAX(bm.harga_beli) AS harga_tertinggi,
        MAX(bm.tanggal_masuk) AS pengiriman_terakhir
    FROM koptumbuh.barang_masuk_produk bm
    WHERE COALESCE(bm.status, '') NOT IN ('Rejected', 'Cancelled')
    GROUP BY bm.pemasok_id, bm.produk_sample_id, bm.koperasi_ref
)
SELECT
    s.koperasi_ref,
    s.pemasok_id,
    s.nama_pemasok,
    s.lead_time_hari AS lead_time_dijanjikan,
    COALESCE(AVG(od.rata_rata_lead_time_aktual), 0) AS lead_time_aktual_rata_rata,
    -- Reliability: actual vs promised (lower is better, 1.0 = perfect)
    CASE WHEN s.lead_time_hari > 0 AND AVG(od.rata_rata_lead_time_aktual) > 0
         THEN ROUND((s.lead_time_hari::numeric / NULLIF(AVG(od.rata_rata_lead_time_aktual), 0))::numeric, 2)
         ELSE NULL END AS rasio_keandalan,
    COUNT(DISTINCT od.produk_sample_id) AS produk_disuplai,
    SUM(od.total_pengiriman) AS total_pengiriman,
    -- On-time score: % of deliveries within promised lead time (approximation)
    ROUND(
        (COUNT(*) FILTER (WHERE od.rata_rata_lead_time_aktual <= s.lead_time_hari)::numeric
         / NULLIF(COUNT(*), 0) * 100)::numeric, 1
    ) AS persentase_tepat_waktu,
    AVG(od.rata_rata_harga) AS rata_rata_harga,
    MAX(od.pengiriman_terakhir) AS pengiriman_terakhir,
    s.status_aktif
FROM koptumbuh.pemasok_koptumbuh s
LEFT JOIN order_data od ON od.pemasok_id = s.pemasok_id AND od.koperasi_ref = s.koperasi_ref
GROUP BY s.koperasi_ref, s.pemasok_id, s.nama_pemasok, s.lead_time_hari, s.status_aktif;
```

**Supplier metrics this view provides:**

| Metric | What It Tells You |
|--------|-------------------|
| `lead_time_dijanjikan` | What the supplier promised (from `pemasok_koptumbuh.lead_time_hari`) |
| `lead_time_aktual_rata_rata` | What actually happened (from `barang_masuk_produk` dates) |
| `rasio_keandalan` | > 1.0 = faster than promised, < 1.0 = slower than promised |
| `persentase_tepat_waktu` | % of deliveries within promised lead time |
| `produk_disuplai` | How many different products this supplier provides |
| `rata_rata_harga` | Average purchase price — compare across suppliers for the same product |

**Purchase Order Tracking:**

Add a lightweight tracking table (migration — does not modify canonical schema):

```sql
-- Migration: purchase order tracking
CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order (
    po_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    pemasok_id      UUID NOT NULL REFERENCES koptumbuh.pemasok_koptumbuh(pemasok_id),
    status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (status IN ('DRAFT', 'DIKIRIM', 'DITERIMA_SEBAGIAN', 'DITERIMA', 'DIBATALKAN')),
    tanggal_order   DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_estimasi DATE,
    catatan         TEXT,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order_item (
    poi_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po_id           UUID NOT NULL REFERENCES koptumbuh.purchase_order(po_id) ON DELETE CASCADE,
    produk_sample_id TEXT NOT NULL REFERENCES koptumbuh.produk_koperasi(produk_sample_id),
    jumlah_dipesan  NUMERIC(18,3) NOT NULL CHECK (jumlah_dipesan > 0),
    jumlah_diterima NUMERIC(18,3) DEFAULT 0 CHECK (jumlah_diterima >= 0),
    harga_per_unit  NUMERIC(18,2),
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW()
);
```

This gives you: **ordered vs received** tracking. When a `barang_masuk` is recorded against a PO, `jumlah_diterima` increments. When `jumlah_diterima = jumlah_dipesan` for all items, PO status → `DITERIMA`. This closes the procure-to-pay loop.

### Knowledge Management: Member-Facing Access

The data exists in `artikel_pengetahuan`. Currently only accessible via admin dashboard. Add a **read-only mobile endpoint** for anggota:

| Method | Endpoint | Purpose | Role |
|--------|----------|---------|------|
| `GET` | `/mobile/knowledge/search?q=` | Full-text search FAQ, SOP, tips | A, O, P |
| `GET` | `/mobile/knowledge/{id}` | Read a specific article | A, O, P |
| `GET` | `/mobile/knowledge/categories` | List categories (SOP, FAQ, TIPS, BIMBINGAN_USAHA) | A, O, P |

Members can now self-serve answers — "How do I check my savings balance?" "What documents do I need to apply for a loan?" — without asking the operator. The GIN full-text search index on `artikel_pengetahuan` already exists (from the canonical schema), so search is fast.

**New web dashboard pages for these additions:**

| Route | Content |
|-------|---------|
| `/members/segmentation` | RFM tier distribution chart + table — DIAMOND through TIDAK_AKTIF |
| `/supply-chain/supplier-scorecard` | Supplier comparison: on-time %, lead time actual vs promised, price trends |
| `/supply-chain/purchase-orders` | PO list: status, supplier, dates, items ordered vs received |

### Engine 9: Data Quality & Normalization Engine

Raw data from WhatsApp messages and manual entries arrives in inconsistent formats. This engine standardizes everything before it reaches BI views and export. It runs as a Celery task triggered after confirmation.

| Normalization | Examples |
|--------------|----------|
| **Payment methods** | `cash`, `Cash`, `TUNAI`, `tunai` → `Cash` |
| **Product units** | `kg`, `KG`, `kilogram`, `kilo` → `KG` |
| **Status values** | `Paid`, `paid`, `LUNAS`, `lunas` → `Paid` |
| **Product names** | `Beras 5kg`, `BERAS 5 KG`, `beras 5kg` → matched to `produk_sample_id` |
| **Bank names** | `BRI`, `BRI SYARIAH`, `Bank Rakyat Indonesia` → standardized |
| **Phone numbers** | `0812...`, `62812...`, `+62812...` → `62812...` |
| **Date formats** | `10/07`, `10 Juli`, `kemarin` → `2026-07-10` |
| **Missing values** | NULL payment → `Cash` (default for cooperative retail) |

```python
# app/services/normalization_service.py
PAYMENT_NORMALIZATION = {
    "cash": "Cash", "tunai": "Cash", "cash": "Cash",
    "transfer": "Transfer", "tf": "Transfer", "bank": "Transfer",
    "lainnya": "Lainnya", "other": "Lainnya"
}

UNIT_NORMALIZATION = {
    "kg": "KG", "kilogram": "KG", "kilo": "KG", "kgram": "KG",
    "pcs": "PCS", "buah": "PCS", "biji": "PCS", "unit": "PCS",
    "liter": "LITER", "l": "LITER", "lt": "LITER",
    "karung": "KARUNG", "sak": "KARUNG",
    "botol": "BOTOL", "btl": "BOTOL",
    "dus": "DUS", "karton": "DUS", "kardus": "DUS",
}

def normalize_payment(raw: str | None) -> str:
    if not raw:
        return "Cash"  # Default
    return PAYMENT_NORMALIZATION.get(raw.strip().lower(), raw)

def normalize_unit(raw: str | None) -> str:
    if not raw:
        return "PCS"  # Default
    return UNIT_NORMALIZATION.get(raw.strip().lower(), raw)
```

This engine is called in two places:
1. **During validation** (Engine 2) — normalizes AI-extracted values before entity resolution
2. **Before export** (Engine 5) — normalizes confirmed data before SIMKOPDES mapping

### Confidence Handling UX Enhancement

Update the extraction schema to return `ambiguous_fields` with suggestions when confidence is low:

```python
# Enhancement to ai_service.py EXTRACTION_CONFIG
# Add to the response schema:
"ambiguous_fields": types.Schema(
    type=types.Type.ARRAY,
    items=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "field": types.Schema(type=types.Type.STRING),
            "input": types.Schema(type=types.Type.STRING),
            "suggestions": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING)
            )
        }
    )
)
```

When `confidence_score < 0.7` or `ambiguous_fields` is non-empty, the confirmation message includes:
> ⚠️ Beberapa data perlu dikonfirmasi:  
> • "beras raja" → Mungkin: Beras Premium 5kg, Beras Medium 5kg

This replaces the current binary pass/fail approach — the user sees WHAT is ambiguous instead of just getting a rejection.

### Production Deployment Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     CLOUD / VPS (Docker)                          │
│                                                                   │
│  ┌─────────────────┐                                             │
│  │  Nginx / Caddy  │  ← HTTPS termination, reverse proxy          │
│  │  Port 443        │                                             │
│  └───────┬─────────┘                                             │
│          │                                                        │
│  ┌───────┴───────────────────────────────────────────────────┐   │
│  │                    Docker Network                           │   │
│  │                                                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │  FastAPI     │  │  Celery      │  │  Celery Beat │    │   │
│  │  │  :8000       │  │  Worker ×2   │  │  Scheduler   │    │   │
│  │  │  (2 replicas)│  │              │  │              │    │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │   │
│  │         │                 │                  │             │   │
│  │  ┌──────┴─────────────────┴──────────────────┴───────┐    │   │
│  │  │                    Redis 7                         │    │   │
│  │  │  Queue broker + Session cache + Rate limiter       │    │   │
│  │  └──────────────────────┬────────────────────────────┘    │   │
│  │                         │                                  │   │
│  │  ┌──────────────────────┴────────────────────────────┐    │   │
│  │  │               PostgreSQL 15                        │    │   │
│  │  │  koptumbuh schema · 40 tables · 8 views            │    │   │
│  │  │  Connection pool: 10-20                            │    │   │
│  │  └──────────────────────┬────────────────────────────┘    │   │
│  │                         │                                  │   │
│  │  ┌──────────┐  ┌────────┴────────┐  ┌──────────────┐     │   │
│  │  │ MinIO    │  │ Evolution API   │  │ Monitoring   │     │   │
│  │  │ :9000    │  │ :8080           │  │ Logs + Alerts│     │   │
│  │  └──────────┘  └─────────────────┘  └──────────────┘     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Static Hosting                           │    │
│  │  ┌──────────────────┐    ┌──────────────────┐             │    │
│  │  │ Next.js Dashboard│    │ Flutter Mobile   │             │    │
│  │  │ (Vercel/Netlify) │    │ App (.apk/.ipa)  │             │    │
│  │  └──────────────────┘    └──────────────────┘             │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

**Backup strategy (MVP):**
- PostgreSQL: `pg_dump` cron job every 6 hours to MinIO bucket `koptumbuh-backups`
- MinIO: `mc mirror` to a separate bucket or external drive daily
- Evolution API session: Docker volume backup (the QR-code pairing data)
- Restore test: run once during Phase 6 to verify backup integrity

**Monitoring (MVP):**
- `GET /health` endpoint checks DB, Redis, MinIO, Evolution connectivity
- Celery Flower dashboard at `:5555` for queue depth monitoring
- Structured JSON logging with `request_id` per webhook call
- Error tracking: catch and log all Celery task failures to `notifikasi_log` table
- Alert: if queue depth > 100 or failed tasks > 10 in 5 minutes, log CRITICAL

---

### Engine 10: RAT & Village Analytics Engine

The official SIMKOPDES database stores RAT financial reports as rich JSON objects (50+ fields per report) and village data as structured records (8,191 commodities, 1,026 demographic profiles). KopTumbuh upgrades these from static reference data into analyzable, visualized intelligence.

#### RAT Financial Report Structure

All 341 RAT records contain 4 financial JSON documents:

| Column | Content | Example Fields |
|--------|---------|---------------|
| `laporan_posisi_keuangan` | Balance Sheet (JSON) | total_aset, kas_dan_setara_kas, simpanan_pokok, simpanan_wajib, persediaan_sembako, total_liabilitas, total_ekuitas, shu_tahun_berjalan, piutang_usaha_simpan_pinjam, aset_tetap (50+ fields) |
| `laporan_hasil_usaha` | Income Statement (JSON) | total_pendapatan, total_beban, shu_sebelum_pajak, shu_tahun_berjalan, hpp_anggota_sembako, beban_kepegawaian, beban_rapat_anggota, pendapatan_anggota_simpan_pinjam (50+ fields) |
| `rapb_posisi_keuangan` | Budget Balance Sheet (JSON) | Same structure as laporan_posisi_keuangan — planned values |
| `rapb_hasil_usaha` | Budget Income Statement (JSON) | Same structure as laporan_hasil_usaha — planned values |

**Status workflow**: Drafted → Verified → Reported (Rejected possible). 289 of 341 = Verified.
**Participants**: 0-215 per RAT, average 25.
**Sectors**: Riil, Riil + USP Konvensional, Riil + USP Syariah, KDKMP.
**All records**: tahun_buku 2025.

#### New RAT Analytics Views

```sql
-- v_rat_shu_summary: SHU (profit/loss) per cooperative
CREATE OR REPLACE VIEW koptumbuh.v_rat_shu_summary AS
SELECT
    r.koperasi_ref, p.nama_koperasi, r.tahun_buku, r.status_rat,
    r.tanggal_rat, r.jumlah_peserta_rat,
    (r.laporan_hasil_usaha::jsonb->>'shu_tahun_berjalan')::numeric AS shu_tahun_berjalan,
    (r.laporan_hasil_usaha::jsonb->>'total_pendapatan')::numeric AS total_pendapatan,
    (r.laporan_hasil_usaha::jsonb->>'total_beban')::numeric AS total_beban,
    (r.laporan_posisi_keuangan::jsonb->>'total_aset')::numeric AS total_aset,
    (r.laporan_posisi_keuangan::jsonb->>'total_liabilitas')::numeric AS total_liabilitas,
    (r.laporan_posisi_keuangan::jsonb->>'total_ekuitas')::numeric AS total_ekuitas,
    (r.laporan_posisi_keuangan::jsonb->>'simpanan_anggota')::numeric AS simpanan_anggota,
    CASE WHEN (r.laporan_hasil_usaha::jsonb->>'shu_tahun_berjalan')::numeric > 0
         THEN 'PROFIT' ELSE 'LOSS' END AS hasil
FROM rat_koperasi r
JOIN profil_koperasi p ON p.koperasi_ref = r.koperasi_ref
WHERE r.laporan_hasil_usaha IS NOT NULL;

-- v_rat_financial_health: Key financial ratios
CREATE OR REPLACE VIEW koptumbuh.v_rat_financial_health AS
SELECT *,
    CASE WHEN total_ekuitas > 0 AND total_aset > 0
         THEN ROUND((total_ekuitas / total_aset * 100)::numeric, 1) END AS rasio_kemandirian_persen,
    CASE WHEN total_aset > 0 AND total_liabilitas > 0
         THEN ROUND((total_aset / total_liabilitas)::numeric, 2) END AS rasio_likuiditas,
    CASE WHEN total_pendapatan > 0
         THEN ROUND((shu_tahun_berjalan / total_pendapatan * 100)::numeric, 1) END AS margin_shu_persen
FROM v_rat_shu_summary;

-- v_rat_comparison: Actual vs Budget comparison
CREATE OR REPLACE VIEW koptumbuh.v_rat_comparison AS
SELECT
    r.koperasi_ref, r.tahun_buku,
    (r.laporan_hasil_usaha::jsonb->>'total_pendapatan')::numeric AS pendapatan_aktual,
    (r.rapb_hasil_usaha::jsonb->>'total_pendapatan')::numeric AS pendapatan_anggaran,
    (r.laporan_hasil_usaha::jsonb->>'total_pendapatan')::numeric
    - (r.rapb_hasil_usaha::jsonb->>'total_pendapatan')::numeric AS selisih_pendapatan
FROM rat_koperasi r
WHERE r.rapb_hasil_usaha IS NOT NULL;
```

#### Village Data Views

```sql
-- v_potensi_desa: Village economic potential ranking
CREATE OR REPLACE VIEW koptumbuh.v_potensi_desa AS
SELECT
    rw.kode_wilayah, rw.desa_kelurahan, rw.kecamatan, rw.kab_kota, rw.provinsi,
    COUNT(kd.komoditas_ref) AS jumlah_komoditas,
    COALESCE(SUM(kd.nilai_potensi_desa), 0) AS total_potensi_ekonomi,
    pd.total_penduduk, pd.anggaran_dana_desa
FROM referensi_wilayah rw
LEFT JOIN referensi_komoditas_desa kd ON kd.kode_wilayah = rw.kode_wilayah
LEFT JOIN referensi_profil_desa pd ON pd.kode_wilayah = rw.kode_wilayah
GROUP BY rw.kode_wilayah, rw.desa_kelurahan, rw.kecamatan,
         rw.kab_kota, rw.provinsi, pd.total_penduduk, pd.anggaran_dana_desa;

-- v_demografi_desa: Village demographics by kabupaten
CREATE OR REPLACE VIEW koptumbuh.v_demografi_desa AS
SELECT
    rw.provinsi, rw.kab_kota,
    COUNT(DISTINCT rw.kode_wilayah) AS jumlah_desa,
    SUM(pd.total_penduduk) AS total_populasi,
    SUM(pd.penduduk_laki_laki) AS total_laki,
    SUM(pd.penduduk_perempuan) AS total_perempuan,
    AVG(pd.total_penduduk)::int AS rata_rata_populasi_per_desa,
    SUM(pd.anggaran_dana_desa) AS total_dana_desa
FROM referensi_wilayah rw
JOIN referensi_profil_desa pd ON pd.kode_wilayah = rw.kode_wilayah
GROUP BY rw.provinsi, rw.kab_kota;
```

#### New Dashboard Pages

| Route | Content |
|-------|---------|
| `/rat` | All RAT records: filter by status, year. SHU summary chart (profit vs loss). |
| `/rat/[id]` | **RAT detail viewer** — parsed financial tables: Balance Sheet, Income Statement, Budget vs Actual. Color-coded rows. |
| `/rat/compare` | Side-by-side RAT comparison or actual vs budget (RAPB) |
| `/village` | Village economic potential ranking, population stats, dana desa distribution |
| `/village/[kode_wilayah]` | Single village detail: commodities, demographics, budget |

#### New API Endpoints

| Endpoint | View/Source | Purpose |
|----------|------------|---------|
| `GET /admin/rat` | rat_koperasi | All RAT records, filterable |
| `GET /admin/rat/{id}` | rat_koperasi | Single RAT with parsed financial JSON |
| `GET /admin/rat/shu-summary` | v_rat_shu_summary | SHU across cooperatives |
| `GET /admin/rat/financial-health` | v_rat_financial_health | Financial ratios |
| `GET /admin/rat/compare` | v_rat_comparison | Budget vs actual |
| `GET /admin/village/potential` | v_potensi_desa | Economic potential ranking |
| `GET /admin/village/demographics` | v_demografi_desa | Population & budget summary |
| `GET /admin/kbli` | kbli_koperasi | KBLI code search (1,184 unique codes) |
| `GET /admin/kbli/{id}` | kbli_koperasi | Single KBLI detail |

**Loans (Pinjaman):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET /admin/loans` | pinjaman_anggota | All loans, filterable by status, member |
| `GET /admin/loans/{id}` | pinjaman_anggota | Single loan detail + payment history |
| `POST /admin/loans` | pinjaman_anggota | Create new loan for member |
| `PATCH /admin/loans/{id}` | pinjaman_anggota | Update loan status (AKTIF, LUNAS, MACET) |

**Employees (Karyawan):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET /admin/employees` | karyawan_koperasi | All employees, filterable |
| `POST /admin/employees` | karyawan_koperasi | Add employee |
| `PATCH /admin/employees/{id}` | karyawan_koperasi | Update employee |

**Banners:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET /admin/banners` | banner | All banners (active/inactive) |
| `POST /admin/banners` | banner | Create banner |
| `PATCH /admin/banners/{id}` | banner | Update banner status |

**Helpdesk / Pengaduan Anggota:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET /admin/complaints` | pengaduan | All member complaints |
| `GET /admin/complaints/{id}` | pengaduan | Single complaint detail |
| `PATCH /admin/complaints/{id}` | pengaduan | Update status (BARU, PROSES, SELESAI) |

**Regional Data (Wilayah API):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET /admin/wilayah/provinces` | referensi_wilayah | All provinces |
| `GET /admin/wilayah/provinces/{id}/districts` | referensi_wilayah | Districts in a province |
| `GET /admin/wilayah/districts/{id}/subdistricts` | referensi_wilayah | Subdistricts in a district |
| `GET /admin/wilayah/subdistricts/{id}/villages` | referensi_wilayah | Villages in a subdistrict |

#### SHU Engine: Real-Time Profitability Estimation

The official SIMKOPDES only calculates SHU once per year during RAT. 80% of cooperatives report losses — but they don't know until the annual meeting. KopTumbuh provides **real-time SHU estimation** from daily transaction data.

**How SHU is calculated (from official RAT JSON structure):**

```
PENDAPATAN (Revenue):
  + pendapatan_anggota_sembako        (member grocery sales)
  + pendapatan_non_anggota_sembako    (non-member grocery sales)
  + pendapatan_anggota_simpan_pinjam  (member savings & loan interest)
  + pendapatan_anggota_apotek_desa    (member pharmacy sales)
  + pendapatan_anggota_logistik       (member logistics revenue)
  + pendapatan_anggota_usaha_lainnya  (other business revenue)
  + hasil_investasi                   (investment returns)
  + pendapatan_lain_lain_*            (other income)

BEBAN (Costs):
  - hpp_anggota_sembako              (COGS - member grocery)
  - hpp_non_anggota_sembako          (COGS - non-member grocery)
  - hpp_anggota_apotek_obat_murah    (COGS - pharmacy)
  - hpp_anggota_logistik             (COGS - logistics)
  - beban_kepegawaian                (staff costs)
  - beban_gaji_pengurus_pengawas     (board salary)
  - beban_rapat_anggota              (RAT meeting cost)
  - beban_pelatihan                  (training cost)
  - beban_administrasi_dan_umum      (admin & general)
  - beban_penyusutan_dan_amortisasi  (depreciation)
  - beban_pajak_penghasilan          (income tax)
  - beban_operasional_lain_lain      (other operational)

= SHU_SEBELUM_PAJAK
- beban_pajak_penghasilan
= SHU_TAHUN_BERJALAN  (Net Profit/Loss for the Year)
```

**Real-time SHU estimation view:**

```sql
-- v_shu_estimasi: Real-time SHU from daily transaction data
CREATE OR REPLACE VIEW koptumbuh.v_shu_estimasi AS
WITH revenue AS (
    SELECT
        t.koperasi_ref,
        DATE_TRUNC('month', COALESCE(t.tanggal_dibuat, t.dibuat_pada)) AS bulan,
        -- Revenue from sales (member + non-member)
        SUM(COALESCE(t.total_pembayaran, 0)) AS total_omzet,
        COUNT(DISTINCT t.transaksi_sample_id) AS jumlah_transaksi,
        -- Member vs non-member split
        SUM(CASE WHEN r.relationship_type = 'MEMBER_CUSTOMER'
            THEN COALESCE(t.total_pembayaran, 0) ELSE 0 END) AS omzet_anggota,
        SUM(CASE WHEN r.relationship_type = 'NON_MEMBER_CUSTOMER' OR r.anggota_ref IS NULL
            THEN COALESCE(t.total_pembayaran, 0) ELSE 0 END) AS omzet_non_anggota
    FROM transaksi_penjualan t
    LEFT JOIN relasi_transaksi_pihak r
        ON r.transaksi_sample_id = t.transaksi_sample_id
    WHERE COALESCE(t.status_transaksi, '') NOT IN ('Refund', 'Cancelled')
    GROUP BY t.koperasi_ref, DATE_TRUNC('month', COALESCE(t.tanggal_dibuat, t.dibuat_pada))
),
costs AS (
    SELECT
        koperasi_ref,
        DATE_TRUNC('month', COALESCE(tanggal_masuk, dibuat_pada)) AS bulan,
        SUM(COALESCE(total_biaya, 0)) AS total_pembelian,
        SUM(COALESCE(jumlah_masuk, 0) * COALESCE(harga_beli, 0)) AS estimasi_hpp
    FROM barang_masuk_produk
    WHERE COALESCE(status, '') NOT IN ('Rejected', 'Cancelled')
    GROUP BY koperasi_ref, DATE_TRUNC('month', COALESCE(tanggal_masuk, dibuat_pada))
)
SELECT
    COALESCE(r.koperasi_ref, c.koperasi_ref) AS koperasi_ref,
    COALESCE(r.bulan, c.bulan) AS bulan,
    COALESCE(r.total_omzet, 0) AS total_pendapatan,
    COALESCE(r.jumlah_transaksi, 0) AS jumlah_transaksi,
    COALESCE(r.omzet_anggota, 0) AS pendapatan_anggota,
    COALESCE(r.omzet_non_anggota, 0) AS pendapatan_non_anggota,
    COALESCE(c.total_pembelian, 0) AS total_pembelian,
    COALESCE(c.estimasi_hpp, 0) AS estimasi_hpp,
    COALESCE(r.total_omzet, 0) - COALESCE(c.estimasi_hpp, 0) AS estimasi_laba_kotor,
    -- Estimated SHU: gross profit minus estimated overhead (simplified for MVP)
    (COALESCE(r.total_omzet, 0) - COALESCE(c.estimasi_hpp, 0)) * 0.85 AS estimasi_shu
FROM revenue r
FULL OUTER JOIN costs c ON c.koperasi_ref = r.koperasi_ref AND c.bulan = r.bulan
ORDER BY bulan DESC;
```

**Why real-time SHU matters:**
- 273 cooperatives (80%) report losses at RAT — they find out once a year
- With daily SHU estimation, operators see problems in real-time: "Your estimated SHU margin is dropping. HPP is 72% of revenue this month vs 65% last month."
- The BI dashboard can show SHU trend: month-over-month, year-over-year
- Before RAT, the operator already knows the numbers — no surprises

#### Automated RAT Report Generator

Generate the 4 JSON financial reports from KopTumbuh transaction data. One click instead of manual compilation.

```python
# app/services/rat_generator.py
async def generate_rat_report(koperasi_ref: str, tahun_buku: int) -> dict:
    """
    Generate RAT financial JSON from KopTumbuh operational data.
    Output matches the official SIMKOPDES laporan_posisi_keuangan structure.
    """
    # Aggregate all transaction data for the fiscal year
    sales = await get_annual_sales(koperasi_ref, tahun_buku)
    purchases = await get_annual_purchases(koperasi_ref, tahun_buku)
    savings = await get_member_savings(koperasi_ref, tahun_buku)
    inventory = await get_current_inventory(koperasi_ref)
    assets = await get_asset_values(koperasi_ref)

    # Build laporan_posisi_keuangan (Balance Sheet)
    laporan_posisi_keuangan = {
        "total_aset": inventory["total_nilai_stok"] + assets["total_aset_tetap"] + sales["kas_dan_setara_kas"],
        "kas_dan_setara_kas": sales["kas_dan_setara_kas"],
        "simpanan_pokok": savings["total_simpanan_pokok"],
        "simpanan_wajib": savings["total_simpanan_wajib"],
        "simpanan_anggota": savings["total_simpanan"],
        "persediaan_sembako": inventory["nilai_stok_sembako"],
        "piutang_usaha_simpan_pinjam": savings["total_piutang"],
        "total_liabilitas": savings["total_simpanan"] + purchases["total_hutang_usaha"],
        "total_ekuitas": savings["total_simpanan_pokok"] + savings["total_simpanan_wajib"] + sales["shu_estimasi"],
        "shu_tahun_berjalan": sales["shu_estimasi"],
        # ... 40+ more fields auto-populated
    }

    # Build laporan_hasil_usaha (Income Statement)
    laporan_hasil_usaha = {
        "total_pendapatan": sales["total_omzet"],
        "total_beban": purchases["total_pembelian"] + sales["total_beban_operasional"],
        "shu_sebelum_pajak": sales["laba_kotor"] - sales["total_beban_operasional"],
        "shu_tahun_berjalan": sales["shu_estimasi"],
        "pendapatan_anggota_sembako": sales["omzet_anggota"],
        "pendapatan_non_anggota_sembako": sales["omzet_non_anggota"],
        "hpp_anggota_sembako": purchases["hpp_anggota"],
        "hpp_non_anggota_sembako": purchases["hpp_non_anggota"],
        "beban_kepegawaian": sales["beban_kepegawaian"],
        "beban_rapat_anggota": sales.get("beban_rat", 0),
        # ... 40+ more fields auto-populated
    }

    return {
        "laporan_posisi_keuangan": laporan_posisi_keuangan,
        "laporan_hasil_usaha": laporan_hasil_usaha,
        "rapb_posisi_keuangan": None,  # Requires budget input
        "rapb_hasil_usaha": None
    }
```

#### Benchmarking API

Compare a cooperative's performance against national averages:

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/benchmark/shu` | Compare this koperasi's SHU margin vs sector average |
| `GET /admin/benchmark/revenue` | Revenue per member vs national average |
| `GET /admin/benchmark/efficiency` | HPP ratio, operational cost ratio vs peers |

```python
# app/services/benchmark_service.py
async def get_shu_benchmark(koperasi_ref: str) -> dict:
    my_shu_margin = await get_my_shu_margin(koperasi_ref)
    sector_avg = 12.5  # From official DB: avg SHU margin for KDKMP

    return {
        "my_shu_margin_persen": my_shu_margin,
        "sector_average_persen": sector_avg,
        "percentile": 65 if my_shu_margin > sector_avg else 35,
        "insight": "SHU margin Anda di atas rata-rata sektor. Pertahankan!" if my_shu_margin > sector_avg
                   else "SHU margin Anda di bawah rata-rata. Periksa HPP dan beban operasional.",
        "top_performers_shu_margin": 85.0  # Top 10% margin
    }
```

#### New Dashboard Pages

| Route | Content |
|-------|---------|
| `/rat/generate` | **RAT report generator** — select tahun_buku, click generate → downloads JSON or submits to `rat_koperasi` |
| `/analytics/shu` | Real-time SHU estimation chart, month-over-month, SHU margin trend |
| `/analytics/benchmark` | Compare cooperative metrics against sector averages |
| `/analytics/revenue-breakdown` | Revenue by business unit (sembako, apotek, simpan_pinjam, etc.) from transaction data |

#### New API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/shu/estimate` | Real-time SHU estimate from transaction data (v_shu_estimasi) |
| `POST /admin/rat/generate` | Generate RAT financial JSON for a tahun_buku |
| `GET /admin/benchmark/shu` | SHU margin vs sector average |
| `GET /admin/benchmark/revenue` | Revenue per member benchmarking |
| `GET /admin/analytics/revenue-breakdown` | Revenue by business unit / gerai type |

---

---

## Automation Priorities — The 8 Automations That Matter

Based on analysis of 1,026 cooperatives with <1 transaction each, 74K placeholder member names, and 372K UNPAID savings records, only 8 automations deliver real operational impact within the constraints of Indonesian village cooperatives.

### Priority Ranking

| Priority | # | Automation | Trigger | Outcome | Feasibility |
|----------|---|-----------|---------|---------|-------------|
| **P0** | 1 | WhatsApp TX Recording + Offline Queue | WhatsApp message or offline form | From <1 TX to 50-100/day per koperasi | Core feature, already built |
| **P0** | 2 | Credit/Hutang Sales | WhatsApp: "bayar nanti, jatuh tempo..." | Covers 70%+ of rural sales. Without this, no adoption. | New in plan — status_transaksi='Unpaid' + jatuh_tempo |
| **P1** | 3 | Stockout Alert | Celery Beat every 4h | Restock before stock hits zero | Already built in Engine 3 |
| **P1** | 4 | RAT Auto-Generation | Operator clicks "Generate" | 3 days manual → 3 seconds | Already built in Engine 10 |
| **P1** | 5 | Price Change Alert | On barang_masuk with higher harga_beli | "Harga beli Beras naik 8%. Naikkan harga jual?" | New in plan — v_harga_berubah |
| **P2** | 6 | Stock Count Reminder | Celery Beat every 7 days | "Stok opname? Balas OPNAME" → penyesuaian_stok | New in plan — prevents inventory drift |
| **P2** | 7 | Identity Resolution | On every confirmed TX | Replace "SAMPLE-ANGGOTA" with real names over time | Phone-number matching, already in webhook |
| **P2** | 8 | Savings Reminder | Cron: 1st of month | WhatsApp: "Simpanan wajib bulan ini sudah jatuh tempo" | One-way notification — member still pays in person |

### What We Dropped and Why

| Dropped | Original Idea | Why It Doesn't Work |
|---------|-------------|-------------------|
| Supplier Price Comparison | Compare prices across suppliers | Most cooperatives have 1 supplier per category. No comparison to make. |
| Village Commodity Matching | Match komoditas_desa to product catalog | Data is government survey (Rp 0 values), not real market data. |
| Cross-Cooperative Benchmarking | Compare SHU margins | Requires 10+ active cooperatives. MVP has 1. Post-MVP. |
| Auto Savings Payment | WhatsApp → auto PAID | Members must physically bring cash. Cannot auto-collect. |
| Member Re-engagement Promo | WhatsApp "Promo untuk Anda" | No promo system, no consent tracking. Legal risk. |

### Projected Impact

| Metric | Current | After 8 Automations |
|--------|---------|-------------------|
| TX per cooperative | <1 (lifetime) | 50-100/day |
| Data capture method | Manual forms | WhatsApp + offline queue |
| Credit sales | Not tracked | Tracked with auto piutang view |
| Stock accuracy | Unknown | Reconciled weekly with auto reminders |
| RAT compilation | 3 days manual | 3 seconds auto-generated |
| Price/margin visibility | None | Real-time alert on cost changes |
| Member data quality | "SAMPLE-ANGGOTA" | Gradual replacement with real names |

### Engine 11: Competitive Price Intelligence

Two automated data sources ensure cooperative prices are compared against the market — **zero operator effort required**.

#### Data Source 1: PIHPS Government API (Free, Official, Daily)

Badan Pangan Nasional publishes daily commodity prices across 500+ traditional markets in Indonesia. Covers 20+ staple commodities: Beras, Minyak Goreng, Gula Pasir, Telur, Daging Ayam, Cabai, Bawang, Tepung.

```python
# app/services/pihps_service.py
import httpx
from app.config import settings

class PIHPSService:
    """Pull daily commodity prices from government API"""
    BASE_URL = "https://panelharga.badanpangan.go.id/api"

    async def get_prices_by_kabupaten(self, kab_kota: str, date: str) -> list[dict]:
        """Get all commodity prices for a kabupaten on a specific date."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/harga",
                params={"kabupaten": kab_kota, "tanggal": date}
            )
            return resp.json()["data"]

    async def match_to_products(self, koperasi_ref: str):
        """
        Match government commodity names to produk_koperasi.
        PIHPS uses: "Beras Premium", "Minyak Goreng Kemasan", "Gula Pasir"
        We normalize via Engine 9's unit/payment normalization.
        """
        products = get_products(koperasi_ref)
        today_prices = await self.get_prices_by_kabupaten(get_kab_kota(koperasi_ref), date.today())

        for p in products:
            matched = fuzzy_match(p.nama_produk, today_prices, threshold=0.6)
            if matched:
                store = HargaPasar(
                    produk_sample_id=p.produk_sample_id,
                    nama_produk_mentah=matched["nama_komoditas"],
                    harga=matched["harga"],
                    nama_toko=f"Pasar {matched['nama_pasar']}",
                    jenis_toko='PASAR',
                    kab_kota=get_kab_kota(koperasi_ref),
                    sumber_data='PIHPS_GOVERNMENT',
                    tanggal_lapor=date.today()
                )
                db.add(store)
        db.commit()
```

#### Data Source 2: E-Commerce Scraping (Automated Daily)

Tokopedia and Shopee list groceries with visible prices. A Celery Beat task scrapes matching product prices daily.

```python
# app/workers/price_scraper.py
import httpx
from bs4 import BeautifulSoup

@celery_app.task
def scrape_ecommerce_prices(koperasi_ref: str):
    """Daily: scrape e-commerce for matching products in same kabupaten."""
    products = get_products(koperasi_ref)
    kab_kota = get_kab_kota(koperasi_ref)

    for p in products:
        # Tokopedia search
        results = search_tokopedia(p.nama_produk, kab_kota)
        for r in results[:5]:
            store = HargaPasar(
                produk_sample_id=p.produk_sample_id,
                nama_produk_mentah=r.title,
                harga=r.price,
                nama_toko=r.shop_name,
                jenis_toko='E_COMMERCE',
                kab_kota=kab_kota,
                sumber_data='TOKOPEDIA',
                sumber_url=f'https://tokopedia.com/{r.slug}',
                tanggal_lapor=date.today()
            )
            db.add(store)
    db.commit()
```

#### The Single Migration Table

```sql
CREATE TABLE IF NOT EXISTS koptumbuh.harga_pasar (
    harga_pasar_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    produk_sample_id   TEXT REFERENCES koptumbuh.produk_koperasi(produk_sample_id),
    nama_produk_mentah TEXT NOT NULL,
    harga              NUMERIC(18,2) NOT NULL,
    nama_toko          TEXT NOT NULL,
    jenis_toko         TEXT CHECK (jenis_toko IN ('PASAR','MINIMARKET','SUPERMARKET','E_COMMERCE','WARUNG','LAINNYA')),
    kab_kota           TEXT,
    sumber_data        TEXT,      -- 'PIHPS_GOVERNMENT' | 'TOKOPEDIA' | 'SHOPEE' | 'MANUAL'
    sumber_url         TEXT,
    tanggal_lapor      TIMESTAMPTZ DEFAULT NOW(),
    kadaluarsa_pada    TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX idx_harga_pasar_produk ON koptumbuh.harga_pasar(produk_sample_id, tanggal_lapor DESC);
```

#### Comparison View

```sql
CREATE OR REPLACE VIEW koptumbuh.v_perbandingan_harga AS
WITH our_price AS (
    SELECT DISTINCT ON (produk_sample_id)
        produk_sample_id, harga_jual
    FROM barang_masuk_produk
    WHERE COALESCE(status,'') NOT IN ('Rejected','Cancelled')
    ORDER BY produk_sample_id, tanggal_masuk DESC
),
market_avg AS (
    SELECT produk_sample_id,
        COUNT(*) AS jumlah_sumber,
        ROUND(AVG(harga), 0) AS harga_pasar_rata,
        MIN(harga) AS harga_terendah,
        MAX(harga) AS harga_tertinggi,
        MAX(tanggal_lapor) AS data_terbaru
    FROM harga_pasar
    WHERE kadaluarsa_pada > NOW()
    GROUP BY produk_sample_id
)
SELECT p.produk_sample_id, p.nama_produk,
    op.harga_jual AS harga_kita,
    ma.harga_pasar_rata, ma.harga_terendah, ma.harga_tertinggi,
    ma.jumlah_sumber, ma.data_terbaru,
    CASE WHEN ma.harga_pasar_rata IS NOT NULL AND ma.harga_pasar_rata > 0
         THEN ROUND(((ma.harga_pasar_rata - op.harga_jual) / ma.harga_pasar_rata * 100)::numeric, 1)
         ELSE NULL END AS selisih_persen,
    CASE WHEN ma.harga_terendah IS NULL THEN 'NO_DATA'
         WHEN op.harga_jual <= ma.harga_terendah THEN 'TERMURAH'
         WHEN op.harga_jual <= ma.harga_pasar_rata THEN 'KOMPETITIF'
         ELSE 'LEBIH_MAHAL' END AS status_harga
FROM produk_koperasi p
JOIN our_price op ON op.produk_sample_id = p.produk_sample_id
LEFT JOIN market_avg ma ON ma.produk_sample_id = p.produk_sample_id;
```

#### Dashboard Widget

```
┌──────────────────────────────────────────────────────────────┐
│  💰 Perbandingan Harga — Kecamatan Cibinong                    │
│                                                                │
│  Sumber: PIHPS (Pemerintah) + Tokopedia/Shopee (E-Commerce)    │
│  Diperbarui: otomatis setiap hari                              │
│                                                                │
│  Beras Premium 5kg                            ✅ TERMURAH       │
│  Kita: Rp 65.000  │  Pasar: Rp 71.500         (10% lebih murah)│
│  7 sumber  ·  terbaru 10 Jul 2026                               │
│                                                                │
│  Minyak Goreng 2L                             ⚠️ LEBIH MAHAL    │
│  Kita: Rp 28.000  │  Pasar: Rp 27.200         (3% lebih mahal) │
│  5 sumber  ·  terbaru 10 Jul 2026                               │
│  💡 Saran: Naikkan ke Rp 28.500 masih kompetitif                │
│                                                                │
│  Gula Pasir 1kg                                TIDAK ADA DATA    │
│  Tidak ada perbandingan tersedia                                │
└──────────────────────────────────────────────────────────────┘
```

#### Celery Beat Schedule

```python
celery_app.conf.beat_schedule = {
    # ... existing schedules ...
    "scrape-ecommerce-prices": {
        "task": "app.workers.price_scraper.scrape_ecommerce_prices",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    "pull-pihps-prices": {
        "task": "app.workers.price_scraper.pull_pihps_prices",
        "schedule": crontab(hour=6, minute=30),  # Daily at 6:30 AM
    },
    "morning-price-broadcast": {
        "task": "app.workers.dispatcher.send_morning_broadcast",
        "schedule": crontab(hour=7, minute=0),  # Daily at 7 AM
    },
    "daily-operator-briefing": {
        "task": "app.workers.recommendations.generate_daily_briefing",
        "schedule": crontab(hour=7, minute=15),  # Daily at 7:15 AM
    },
    "auto-generate-purchase-orders": {
        "task": "app.workers.supply_chain.auto_generate_po",
        "schedule": crontab(hour=7, minute=30),  # Daily at 7:30 AM
    },
}
```

#### New API & Dashboard

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/price-comparison` | Comparison view per product |
| `GET /admin/price-comparison/history` | Price trends over time |

| Dashboard Page | Content |
|---------------|---------|
| `/analytics/price-comparison` | Live comparison table with status badges, suggested price adjustments |

**What this does to operational volume:** The dashboard answers "Are we the cheapest?" automatically. If the cooperative has a 10% price advantage on Beras, the operator puts up a sign. Members choose the cooperative over Indomaret for those products. This is the most direct lever to increase transaction volume — price visibility drives foot traffic.

---

## Pre-Flight: Development Environment Setup (Hour 0 — Before Any Code)

Complete this before touching any application code. Every developer on the team should be able to run `docker compose up` and see all services healthy.

### Step 1: Repository Setup (10 min)

```bash
# Option A: Monorepo (recommended for hackathon — one repo, three folders)
git init koptumbuh
cd koptumbuh
mkdir backend web-dashboard database docs
git add -A && git commit -m "chore: initialize KopTumbuh monorepo"

# Branch naming convention:
#   feat/phase-1-db     feat/phase-2-webhook    feat/phase-3-confirm
#   feat/phase-4-web     feat/phase-5-engine     feat/phase-6-test
# Mobile app lives in a separate repo (built by mobile dev)

# Commit convention: conventional commits
#   feat: add webhook endpoint
#   fix: handle duplicate message_id
#   chore: update dependencies
#   docs: add API contract for mobile
```

### Step 2: Docker & Services (15 min)

```bash
# Prerequisites: Docker Desktop (or Docker + docker-compose) installed
docker --version  # Must be 24+
docker compose version

# Copy .env.example and fill in values
cp backend/.env.example backend/.env
# REQUIRED: GEMINI_API_KEY (from Google AI Studio)
# REQUIRED: EVOLUTION_API_KEY (any random string — your choice)
# REQUIRED: JWT_SECRET_KEY (generate: openssl rand -hex 32)

# Start all services
cd backend
docker compose up -d

# Wait for healthy state (all 4 services)
docker compose ps
# EXPECTED: postgres (healthy), redis (healthy), minio (healthy), evolution (healthy)

# Verify PostgreSQL schema loaded
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='koptumbuh';"
# EXPECTED: 40 (canonical schema tables loaded from init script)

# Verify Redis
docker exec koptumbuh-cache redis-cli ping
# EXPECTED: PONG
```

### Step 3: Ngrok Tunnel for WhatsApp Webhooks (5 min)

```bash
# WhatsApp webhooks need a PUBLIC URL. Ngrok creates a tunnel to localhost.
# Install: https://ngrok.com/download
# Or use: npx localtunnel --port 8000 (free alternative)

ngrok http 8000
# Output: https://abc123.ngrok-free.app → http://localhost:8000

# Copy the HTTPS URL. Paste it into Evolution API webhook config:
# Open http://localhost:8080 → your instance → webhook settings
# Webhook URL: https://abc123.ngrok-free.app/api/v1/webhooks/whatsapp
# Events: messages.upsert
```

### Step 4: Evolution API — Pair WhatsApp (5 min)

```bash
# Open Evolution API dashboard
open http://localhost:8080  # or browse manually

# 1. Create instance named "koptumbuh"
# 2. Click "Connect" → QR code appears
# 3. Open WhatsApp on your phone → Settings → Linked Devices → Link a Device
# 4. Scan the QR code
# 5. Wait for "Connected" status

# Verify pairing:
curl http://localhost:8080/instance/connectionState/koptumbuh \
  -H "apikey: ${EVOLUTION_API_KEY}"
# EXPECTED: {"state": "open"}

# Configure webhook (in Evolution dashboard or via API):
curl -X POST http://localhost:8080/webhook/set/koptumbuh \
  -H "apikey: ${EVOLUTION_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "url": "https://abc123.ngrok-free.app/api/v1/webhooks/whatsapp",
    "events": ["messages.upsert"]
  }'
```

### Step 5: Migration Execution Order (5 min)

Migrations must run in this exact order. The canonical schema is auto-loaded by Docker. Additive migrations are applied manually:

```bash
# Order: canonical → role extension → PO tables → new views → seed data
# These run inside the PostgreSQL container:

# 1. Canonical schema — AUTO by docker-entrypoint-initdb.d/01_schema.sql ✅
# 2. Extend role CHECK constraint (add ANGGOTA)
docker exec -i koptumbuh-db psql -U dev_admin -d koptumbuh_dev <<'SQL'
ALTER TABLE koptumbuh.pengguna_koptumbuh DROP CONSTRAINT IF EXISTS pengguna_koptumbuh_role_check;
ALTER TABLE koptumbuh.pengguna_koptumbuh ADD CONSTRAINT pengguna_koptumbuh_role_check
  CHECK (role IN ('OPERATOR','KETUA','BENDAHARA','PEMBINA','ADMIN','ANGGOTA'));
SQL

# 3. Purchase Order tables
docker exec -i koptumbuh-db psql -U dev_admin -d koptumbuh_dev <<'SQL'
CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order ( /* ... full DDL from plan ... */ );
CREATE TABLE IF NOT EXISTS koptumbuh.purchase_order_item ( /* ... full DDL from plan ... */ );
SQL

# 4. New BI & Relationship views (v_margin_produk, v_produk_lambat_bergerak,
#    v_anggota_aktif, v_segmentasi_anggota, v_preferensi_anggota, v_skor_pemasok)
# Run each CREATE OR REPLACE VIEW statement from the plan

# 5. Seed data — AUTO by docker-entrypoint-initdb.d/02_seed.sql ✅
# Verify seed loaded:
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c \
  "SELECT nama_koperasi FROM koptumbuh.profil_koperasi;"
# EXPECTED: Koperasi Tumbuh Bersama
```

### Step 6: Python Environment (15 min)

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
# Verify key packages:
python -c "import fastapi, sqlalchemy, celery, redis, google.genai; print('OK')"
```

### Step 7: Test Database Setup (5 min)

```bash
# Create a SEPARATE test database — never run tests against dev DB
docker exec koptumbuh-db psql -U dev_admin -c "CREATE DATABASE koptumbuh_test;"

# Load schema into test DB (same canonical + extensions)
docker exec -i koptumbuh-db psql -U dev_admin -d koptumbuh_test < \
  database/koptumbuh_updated_minimal_data_model.sql

# Load minimal test seed (not the full demo seed — just enough for tests)
# Set TEST_DATABASE_URL in .env:
# TEST_DATABASE_URL=postgresql+asyncpg://dev_admin:devpassword@localhost:5432/koptumbuh_test
```

### Step 8: Dev-Mode Bypass for Confirmation Testing (5 min)

Testing the YA/UBAH/BATAL flow requires a real WhatsApp round-trip during development. Add a dev-mode endpoint to skip WhatsApp:

```python
# app/api/v1/dev.py — ONLY available when DEBUG=true
@router.post("/dev/simulate-confirmation")
async def simulate_confirmation(parsing_id: str, decision: str):
    """
    Dev-only: simulate a YA/UBAH/BATAL reply without WhatsApp.
    Calls the same state machine handler that the webhook uses.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404)

    # Look up the parsing record
    parsing = get_parsing(parsing_id)
    # Simulate a pesan_masuk with the decision as raw_text
    pesan = parsing.pesan
    pesan.raw_text = decision.upper()

    # Route through the same state machine
    if decision.upper() == "YA":
        await commit_transaction_atomic(parsing, pesan)
    elif decision.upper() == "UBAH":
        parsing.status = "SUPERSEDED"
        db.commit()
        redis_client.delete(f"session:{pesan.pengguna.nomor_whatsapp}")
    elif decision.upper() == "BATAL":
        pesan.status = "CANCELLED"
        db.commit()
        redis_client.delete(f"session:{pesan.pengguna.nomor_whatsapp}")

    return {"success": True, "decision": decision.upper()}
```

### Step 9: Verify Everything (5 min)

```bash
# Run the verification script
python backend/scripts/verify_infra.py
# EXPECTED OUTPUT:
#   ✅ PostgreSQL: connected (40 tables, 8 views in koptumbuh schema)
#   ✅ Redis: connected (SET/GET roundtrip OK)
#   ✅ MinIO: connected (test bucket created)
#   ✅ Evolution API: connected (instance "koptumbuh" is paired)
#   ✅ Gemini API: connected (test completion OK)
#   ✅ Seed data: 1 cooperative, 5 products, 5 members, 5 transactions loaded

# Quick smoke test — send a text message via curl
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "data": {
      "key": {"id": "SMOKE-TEST-001", "remoteJid": "628123456003@s.whatsapp.net"},
      "message": {"conversation": "test message", "messageType": "conversation"}
    }
  }'
# EXPECTED: {"success": true, "data": {"status": "queued", "pesan_id": "..."}}

# Check Celery processed it:
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c \
  "SELECT status, input_type, raw_text FROM koptumbuh.pesan_masuk WHERE whatsapp_message_id = 'SMOKE-TEST-001';"
# EXPECTED: RECEIVED or PROCESSING or PARSED
```

**Pre-Flight complete when:** All 9 steps return green. Every developer has the same environment. The team can now work in parallel on Phases 1-4.

---

## Error Code Catalog

All API errors use a consistent format. Frontend teams build error handling against this catalog:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable Indonesian message",
    "details": { /* optional context */ }
  }
}
```

| HTTP | Error Code | When | Details |
|------|-----------|------|---------|
| 400 | `INVALID_INPUT` | Missing required fields, bad format | `{"fields": ["customer_name", "items"]}` |
| 400 | `TEXT_TOO_LONG` | Text > 4000 characters | `{"max": 4000, "actual": 5234}` |
| 400 | `AUDIO_TOO_LONG` | Audio > 60 seconds | `{"max_seconds": 60, "actual": 95}` |
| 400 | `MEDIA_TOO_LARGE` | File > 10MB | `{"max_mb": 10, "actual_mb": 15.3}` |
| 401 | `UNAUTHORIZED` | Missing or invalid JWT | — |
| 401 | `TOKEN_EXPIRED` | JWT expired, use refresh token | — |
| 403 | `FORBIDDEN` | Role doesn't have access | `{"required_role": "OPERATOR", "actual_role": "ANGGOTA"}` |
| 404 | `PRODUCT_NOT_FOUND` | Product name doesn't match catalog | `{"extracted": "Kopi Arabika", "suggestions": ["Kopi Bubuk 200g"]}` |
| 404 | `MEMBER_NOT_FOUND` | Member name/NIK not found | `{"query": "Pak Joko"}` |
| 404 | `PARSING_NOT_FOUND` | Invalid parsing_id | — |
| 409 | `DUPLICATE_MESSAGE` | wa_message_id already processed | `{"message_id": "wamid.ABC123"}` |
| 409 | `SESSION_EXISTS` | User already has a pending confirmation | `{"existing_parsing_id": "..."}` |
| 422 | `VALIDATION_FAILED` | AI extraction failed checks | `{"errors": ["PRODUCT_NOT_FOUND: Kopi Arabika"]}` |
| 422 | `INSUFFICIENT_STOCK` | Requested qty > available stock | `{"product": "Telur 1kg", "available": 5, "requested": 10}` |
| 422 | `PARSING_FAILED` | Gemini returned invalid JSON | `{"raw_response": "..."}` |
| 429 | `RATE_LIMITED` | Too many requests | `{"retry_after_seconds": 45}` |
| 500 | `INTERNAL_ERROR` | Unexpected server error | `{"request_id": "req-abc123"}` |
| 503 | `SERVICE_UNAVAILABLE` | Gemini/Redis/DB down | `{"service": "gemini"}` |

---

## Phase 1: Infrastructure & Database (Hours 0–6)

### Phase 1 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 1.1 | 30 min | Docker Compose + all 4 services running | Pre-Flight Step 2 | `docker compose ps` all healthy | `docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c "SELECT 1"` |
| 1.2 | 1 hr | Canonical schema migration + seed data loaded | 1.1 | 40 tables + seed data in koptumbuh schema | `SELECT count(*) FROM information_schema.tables WHERE table_schema='koptumbuh'` → 40 |
| 1.3 | 30 min | Dockerfiles (API + Worker) | 1.1 | `Dockerfile.api`, `Dockerfile.worker` | `docker build -f Dockerfile.api .` succeeds |
| 1.4 | 1.5 hr | FastAPI project scaffolding | 1.2 | `app/main.py`, `config.py`, `database.py` running | `uvicorn app.main:app` → `http://localhost:8000/health` returns 200 |
| 1.5 | 2 hr | SQLAlchemy models — all 40 tables mapped | 1.2 | 7 model files in `app/models/` | `python -c "from app.models import *"` imports without error |
| 1.6 | 30 min | `.env.example` + all env vars documented | 1.3 | `.env.example` with all 25+ variables | Each var has a comment explaining its purpose |
| 1.7 | 30 min | Health check + infra verification script | 1.4 | `scripts/verify_infra.py` | Script outputs ✅ for all 5 services |

### 1a. Docker Compose

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    container_name: koptumbuh-db
    environment:
      POSTGRES_DB: koptumbuh_dev
      POSTGRES_USER: dev_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD:-devpassword}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ../database/koptumbuh_updated_minimal_data_model.sql:/docker-entrypoint-initdb.d/01_schema.sql
      - ../database/seed_demo.sql:/docker-entrypoint-initdb.d/02_seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev_admin -d koptumbuh_dev"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: koptumbuh-cache
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: koptumbuh-storage
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minio_admin}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minio_password}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      retries: 5

  evolution:
    image: atendai/evolution-api:latest
    container_name: koptumbuh-evolution
    ports:
      - "8080:8080"
    environment:
      AUTHENTICATION_API_KEY: ${EVOLUTION_API_KEY:-koptumbuh-evolution-key}
      LANGUAGE: en
    volumes:
      - evolution_data:/evolution/instances
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
      interval: 10s
      retries: 5

volumes:
  pgdata:
  minio_data:
  evolution_data:
```

### 1b. Evolution API Setup (WhatsApp)

Evolution API is a self-hosted Docker container that speaks WhatsApp Web protocol (Baileys). No Meta Business account, no token expiry, no business verification. One QR scan and it's paired.

**One-time setup:**
1. Evolution API starts with the Docker Compose stack (`docker compose up -d evolution`).
2. Open `http://localhost:8080` — the Evolution API dashboard loads.
3. Create a new instance named `koptumbuh`.
4. Scan the QR code with WhatsApp on your phone (the number you want as the cooperative line).
5. After pairing, Evolution stores the session in a Docker volume — it survives container restarts.
6. Configure the Evolution webhook to POST to our FastAPI: set webhook URL to `http://api:8000/api/v1/webhooks/whatsapp` and enable `messages.upsert` events.

**API authentication**: Set via `AUTHENTICATION_API_KEY` env var. All our API calls use the `apikey` header.

**Why Evolution over Meta Cloud API:**
- No 24h token expiry (the #1 hackathon demo killer)
- No Meta Business verification required
- Works with any personal WhatsApp number
- Single `whatsapp_service.py` file isolates the transport — swap to Meta Cloud API later by changing only that file

### 1c. Dockerfiles

**Dockerfile.api:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY alembic.ini alembic/ ./alembic/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile.worker:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
```

### 1d. Database Migration & Seed

**Migration**: Copy `koptumbuh_updated_minimal_data_model.sql` to `database/`. Mount as init script. No modifications allowed — this is the SSOT.

**Seed data** (`database/seed_demo.sql`): Full demo scenario — 1 cooperative in Desa Jonggol, Kabupaten Bogor, Jawa Barat (real SIMKOPDES wilayah code `32.01.06.2009`). All ID formats, status values, and reference data match official SIMKOPDES conventions.

```sql
-- ============================================
-- 1. REFERENCE DATA (pulled from official SIMKOPDES DB)
-- ============================================

-- Real wilayah: Desa Jonggol, Kec. Jonggol, Kab. Bogor, Jawa Barat
INSERT INTO referensi_wilayah (kode_wilayah, provinsi, kab_kota, kecamatan, desa_kelurahan)
VALUES ('32.01.06.2009', 'JAWA BARAT', 'KAB. BOGOR', 'Jonggol', 'Jonggol');

-- Real document types from official SIMKOPDES
INSERT INTO referensi_dokumen_koperasi (jenis_dokumen_ref, nama_dokumen) VALUES
    ('JENIS-DOC-F49EF56C92', 'Akta Pendirian'),
    ('JENIS-DOC-E27F233795', 'Akta Pendirian - Perubahan'),
    ('JENIS-DOC-62A46E908D', 'Berita Negara (BN)'),
    ('JENIS-DOC-018B05092C', 'Nomor Induk Berusaha (NIB)'),
    ('JENIS-DOC-BD46961E09', 'Nomor Pokok Wajib Pajak (NPWP)'),
    ('JENIS-DOC-180AA1F25E', 'Surat Keputusan Kemenkumham (SK AHU)'),
    ('JENIS-DOC-8693952152', 'Surat Keputusan Kemenkumham (SK AHU) - Perubahan'),
    ('JENIS-DOC-8693952152aaa', '-');

-- Real outlet types from official SIMKOPDES
INSERT INTO referensi_gerai_koperasi (jenis_gerai_ref, nama_jenis_gerai) VALUES
    ('JENIS-GERAI-9B8BB8396D', 'Apotek Desa'),
    ('JENIS-GERAI-BE6B6A2B01', 'Gerai Cold Storage/Cold Chain'),
    ('JENIS-GERAI-8112C21704', 'Gerai Kantor Koperasi'),
    ('JENIS-GERAI-FDB1681AD5', 'Gerai Klinik Desa'),
    ('JENIS-GERAI-B5D536E874', 'Gerai Sembako (Embrio KopHub)'),
    ('JENIS-GERAI-40F1F69AF4', 'Gerai Unit Usaha Simpan Pinjam (Embrio Kop Bank)'),
    ('JENIS-GERAI-5BB9593DB7', 'Logistik (Distribusi)'),
    ('JENIS-GERAI-CCD4662078', 'Usaha Lainnya (KBLI 2020)');

-- ============================================
-- 2. COOPERATIVE HUB & PROFILE
-- ID format: KOP-JasaAI-{12-HEX}
-- Status: Approved, Primer (matching official SIMKOPDES)
-- ============================================

INSERT INTO referensi_koperasi_wilayah (koperasi_ref, kode_wilayah)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', '32.01.06.2009');

INSERT INTO profil_koperasi (
    koperasi_ref, nama_koperasi, status_registrasi, bentuk_koperasi,
    kategori_usaha, nik_koperasi, alamat_lengkap, kode_pos
) VALUES (
    'KOP-JasaAI-A1B2C3D4E5F6',
    'KOPERASI DESA MERAH PUTIH TUMBUH BERSAMA JONGGOL',
    'Approved', 'Primer',
    'SEMBAKO', '1234567890123456',
    'Jl. Raya Jonggol No. 42, Desa Jonggol, Kec. Jonggol, Kab. Bogor', '16830'
);

-- Board/Management (pengurus_koperasi)
INSERT INTO pengurus_koperasi (
    pengurus_ref, koperasi_ref, nama, jabatan, status, no_hp, nik, jenis_kelamin, email
) VALUES
    ('PENG-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Agus Wijaya', 'KETUA', 'Aktif',
     '628123456001', '3273011234560001', 'LAKI-LAKI', 'agus.wijaya@email.com'),
    ('PENG-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Ratna Dewi', 'BENDAHARA', 'Aktif',
     '628123456002', '3273011234560002', 'PEREMPUAN', 'ratna.dewi@email.com');

-- Employees
INSERT INTO karyawan_koperasi (
    karyawan_ref, koperasi_ref, nama, jabatan, nomor_hp_karyawan, jenis_kelamin, status_karyawan
) VALUES
    ('KAR-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Budi Santoso', 'OPERATOR KASIR',
     '628123456003', 'LAKI-LAKI', 'TETAP'),
    ('KAR-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Siti Rahmawati', 'ADMIN STOK',
     '628123456004', 'PEREMPUAN', 'TETAP');

-- Outlet (using official gerai type)
INSERT INTO gerai_koperasi (
    gerai_ref, koperasi_ref, jenis_gerai_ref, status_gerai,
    akses_internet, akses_listrik, jenis_bangunan
) VALUES (
    'GERAI-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-GERAI-B5D536E874',
    'Aktif', 'Ada', 'Ada', 'PERMANEN'
);

-- KBLI
INSERT INTO kbli_koperasi (koperasi_ref, kode_kbli, nama_kbli, tipe_izin_usaha, tahun_kbli)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', '47111', 'Perdagangan Eceran Sembako', 'Mikro', 2024);

-- Legal Documents
INSERT INTO dokumen_koperasi (
    dokumen_ref, koperasi_ref, jenis_dokumen_ref, nomor, tanggal_berlaku
) VALUES
    ('DOK-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-DOC-F49EF56C92',
     'AHU-0012345.AH.01.01.TAHUN.2023', '2023-06-15'),
    ('DOK-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'JENIS-DOC-BD46961E09',
     '12.345.678.9-012.000', '2023-06-15');

-- RAT (Annual Member Meeting)
INSERT INTO rat_koperasi (
    rat_sample_id, koperasi_ref, jenis_sektor_koperasi, urutan_rat,
    tahun_buku, tahun_rencana_kerja, tahun_rencana_anggaran, tanggal_rat,
    jumlah_peserta_rat, status_rat, tahap_rat
) VALUES (
    'RAT-000342', 'KOP-JasaAI-A1B2C3D4E5F6', 'Perdagangan', 'RAT KE-5',
    2024, 2025, 2025, '2025-01-20', 45, 'Verified', 'PASCA_RAT'
);

-- ============================================
-- 3. USERS (JasaAI_pengguna_koptumbuh on shared DB)
-- Migration: extend CHECK constraint for ANGGOTA role
-- ============================================

INSERT INTO pengguna_koptumbuh (koperasi_ref, pengurus_ref, nama, nomor_whatsapp, role, status_aktif)
VALUES
    ('KOP-JasaAI-A1B2C3D4E5F6', 'PENG-A1B2C3D4E5F6', 'Agus Wijaya', '628123456001', 'KETUA', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'Budi Santoso', '628123456003', 'OPERATOR', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'Ratna Dewi', '628123456002', 'BENDAHARA', TRUE),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'Pak Haji Ahmad', '628120000001', 'ANGGOTA', TRUE);

-- ============================================
-- 4. PRODUCTS & INVENTORY
-- ID format: PROD-{12-HEX} (matching official SIMKOPDES)
-- Prices from barang_masuk (not product master — matching official pattern)
-- ============================================

INSERT INTO produk_koperasi (produk_sample_id, koperasi_ref, kode_barcode, nama_produk, unit)
VALUES
    ('PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', '8991001000001', 'Beras Premium 5kg', 'Kg'),
    ('PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', '8991002000002', 'Minyak Goreng 2L', 'Liter'),
    ('PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', '8991003000003', 'Gula Pasir 1kg', 'Kg'),
    ('PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', '8991004000004', 'Telur Ayam 1kg', 'Kg'),
    ('PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', '8991005000005', 'Mie Instan Dus', 'Dus'),
    ('PROD-F6A1B2C3D4E5', 'KOP-JasaAI-A1B2C3D4E5F6', '8990347787806', 'Minyakita 1L (Subsidi)', 'Liter');

-- Initial stock via barang_masuk
INSERT INTO barang_masuk_produk (
    barang_masuk_ref, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_masuk, jumlah_tersedia, harga_beli, harga_jual, total_biaya, status, tanggal_masuk
) VALUES
    ('BM-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg',
     100, 50, 55000, 65000, 5500000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-B2C3D4E5F6A1', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L',
     60, 30, 24000, 28000, 1440000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-C3D4E5F6A1B2', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg',
     80, 25, 12000, 14000, 960000, 'Diterima', '2026-07-01 08:00:00+07'),
    ('BM-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg',
     40, 15, 23000, 27000, 920000, 'Diterima', '2026-07-03 08:00:00+07'),
    ('BM-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus',
     50, 35, 45000, 52000, 2250000, 'Diterima', '2026-07-01 08:00:00+07');

-- Inventory snapshots
INSERT INTO inventaris_produk (inventaris_ref, produk_sample_id, koperasi_ref, nama_produk, stok)
VALUES
    ('INV-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 50),
    ('INV-B2C3D4E5F6A1', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 30),
    ('INV-C3D4E5F6A1B2', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 25),
    ('INV-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 15),
    ('INV-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 35);

-- ============================================
-- 5. MEMBERS, CUSTOMERS & SUPPLIERS
-- ID format: AGT-{12-HEX}
-- Status: Approved (matching official SIMKOPDES)
-- Gender: LAKI-LAKI / PEREMPUAN (matching official SIMKOPDES)
-- ============================================

INSERT INTO anggota_koperasi (
    anggota_ref, koperasi_ref, nama, nik, kode_wilayah, jenis_kelamin,
    status_keanggotaan, tanggal_terdaftar, pekerjaan
) VALUES
    ('AGT-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Haji Ahmad Suherman',
     '327301******0001', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-01-15', 'Petani'),
    ('AGT-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Siti Nurhaliza',
     '327301******0002', '32.01.06.2009', 'PEREMPUAN', 'Approved', '2024-02-01', 'Pedagang'),
    ('AGT-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Dimas Prayogo',
     '327301******0003', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-03-10', 'Buruh'),
    ('AGT-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Dewi Lestari',
     '327301******0004', '32.01.06.2009', 'PEREMPUAN', 'Approved', '2024-03-15', 'Guru'),
    ('AGT-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Joko Supriyanto',
     '327301******0005', '32.01.06.2009', 'LAKI-LAKI', 'Approved', '2024-04-01', 'Wiraswasta');

-- Member savings (status: PAID/UNPAID — matching official SIMKOPDES)
INSERT INTO simpanan_anggota (
    simpanan_ref, koperasi_ref, anggota_ref, periode_pembayaran, jumlah_simpanan, status
) VALUES
    ('SIMPAN-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Simpanan Wajib - Juli 2026', 50000, 'PAID'),
    ('SIMPAN-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Simpanan Wajib - Juli 2026', 50000, 'PAID'),
    ('SIMPAN-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Simpanan Wajib - Juni 2026', 50000, 'PAID'),
    ('SIMPAN-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Simpanan Wajib - Juni 2026', 50000, 'PAID');

-- Customers (4 members + 1 walk-in)
INSERT INTO pelanggan_koptumbuh (koperasi_ref, anggota_ref, nama_pelanggan, nomor_whatsapp)
VALUES
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-A1B2C3D4E5F6', 'Pak Haji Ahmad', '628120000001'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'Bu Siti Nurhaliza', '628120000002'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-C3D4E5F6A1B2', 'Mas Dimas', '628120000003'),
    ('KOP-JasaAI-A1B2C3D4E5F6', 'AGT-D4E5F6A1B2C3', 'Mbak Dewi', '628120000004'),
    ('KOP-JasaAI-A1B2C3D4E5F6', NULL, 'Pelanggan Umum', NULL);

-- Supplier
INSERT INTO pemasok_koptumbuh (koperasi_ref, nama_pemasok, nomor_hp, alamat, lead_time_hari, payment_term)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6', 'PT Pangan Sejahtera Nusantara', '628120000099',
        'Jl. Raya Bogor KM 45, Bogor', 3, 'NET 30');

-- ============================================
-- 6. HISTORICAL TRANSACTIONS (for dashboard)
-- ID format: TRX-{12-HEX}
-- Status: Paid, Cash/Transfer (matching official SIMKOPDES)
-- ============================================

INSERT INTO transaksi_penjualan (
    transaksi_sample_id, koperasi_ref, nama_pelanggan, tanggal_dibuat,
    total_pembayaran, status_transaksi, metode_pembayaran
) VALUES
    ('TRX-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Bu Siti Nurhaliza',
     '2026-07-03 10:15:00+07', 158000, 'Paid', 'Cash'),
    ('TRX-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pak Haji Ahmad',
     '2026-07-05 14:30:00+07', 270000, 'Paid', 'Cash'),
    ('TRX-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mas Dimas',
     '2026-07-07 09:00:00+07', 65000, 'Paid', 'Transfer'),
    ('TRX-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mbak Dewi',
     '2026-07-08 16:45:00+07', 196000, 'Paid', 'Cash'),
    ('TRX-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Pelanggan Umum',
     '2026-07-09 11:20:00+07', 52000, 'Paid', 'Cash');

-- Line items
INSERT INTO barang_keluar_produk (
    transaksi_sample_id, produk_sample_id, koperasi_ref, nama_produk,
    jumlah_keluar, harga, total_nilai, status_transaksi, tanggal_keluar
) VALUES
    ('TRX-A1B2C3D4E5F6', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 2, 65000, 130000, 'Paid', '2026-07-03 10:15:00+07'),
    ('TRX-A1B2C3D4E5F6', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 1, 28000, 28000, 'Paid', '2026-07-03 10:15:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 3, 65000, 195000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 2, 27000, 54000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-B2C3D4E5F6A1', 'PROD-C3D4E5F6A1B2', 'KOP-JasaAI-A1B2C3D4E5F6', 'Gula Pasir 1kg', 1, 14000, 14000, 'Paid', '2026-07-05 14:30:00+07'),
    ('TRX-C3D4E5F6A1B2', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-07-07 09:00:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-B2C3D4E5F6A1', 'KOP-JasaAI-A1B2C3D4E5F6', 'Minyak Goreng 2L', 3, 28000, 84000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-A1B2C3D4E5F6', 'KOP-JasaAI-A1B2C3D4E5F6', 'Beras Premium 5kg', 1, 65000, 65000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-D4E5F6A1B2C3', 'PROD-D4E5F6A1B2C3', 'KOP-JasaAI-A1B2C3D4E5F6', 'Telur Ayam 1kg', 1, 27000, 27000, 'Paid', '2026-07-08 16:45:00+07'),
    ('TRX-E5F6A1B2C3D4', 'PROD-E5F6A1B2C3D4', 'KOP-JasaAI-A1B2C3D4E5F6', 'Mie Instan Dus', 1, 52000, 52000, 'Paid', '2026-07-09 11:20:00+07');

-- Member-TX links
INSERT INTO relasi_transaksi_pihak (transaksi_sample_id, anggota_ref, relationship_type, match_method)
VALUES
    ('TRX-A1B2C3D4E5F6', 'AGT-B2C3D4E5F6A1', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-B2C3D4E5F6A1', 'AGT-A1B2C3D4E5F6', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-C3D4E5F6A1B2', 'AGT-C3D4E5F6A1B2', 'MEMBER_CUSTOMER', 'auto'),
    ('TRX-D4E5F6A1B2C3', 'AGT-D4E5F6A1B2C3', 'MEMBER_CUSTOMER', 'auto');

-- ============================================
-- 7. SUBSIDIES, KNOWLEDGE & FINAL STOCK UPDATE
-- ============================================

-- Mark subsidized products (Minyakita is government-subsidized)
UPDATE produk_koperasi SET is_subsidi = TRUE, nama_subsidi = 'Minyak Goreng Bersubsidi Pemerintah'
WHERE produk_sample_id = 'PROD-F6A1B2C3D4E5' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';

INSERT INTO artikel_pengetahuan (koperasi_ref, judul, kategori, isi, sumber)
VALUES ('KOP-JasaAI-A1B2C3D4E5F6',
    'SOP Pencatatan Transaksi Harian via WhatsApp',
    'SOP',
    'Kirim pesan dengan format: [Nama Pelanggan] beli [Jumlah] [Nama Produk]. Contoh: Bu Siti beli 2 Beras Premium 5kg, bayar tunai.',
    'JasaAI Admin');

-- Update inventory to reflect demo sales
UPDATE inventaris_produk SET stok = stok - 7 WHERE produk_sample_id = 'PROD-A1B2C3D4E5F6' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = stok - 4 WHERE produk_sample_id = 'PROD-B2C3D4E5F6A1' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = stok - 1 WHERE produk_sample_id = 'PROD-C3D4E5F6A1B2' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = stok - 3 WHERE produk_sample_id = 'PROD-D4E5F6A1B2C3' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
UPDATE inventaris_produk SET stok = stok - 1 WHERE produk_sample_id = 'PROD-E5F6A1B2C3D4' AND koperasi_ref = 'KOP-JasaAI-A1B2C3D4E5F6';
```

### 1e. FastAPI Scaffolding

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify DB, Redis, MinIO connections
    yield
    # Shutdown: close connections

app = FastAPI(title="KopTumbuh API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # ["http://localhost:3000", "exp://..."]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health():
    return {"status": "ok", "db": "connected", "redis": "connected", "minio": "connected"}
```

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://dev_admin:devpassword@localhost:5432/koptumbuh_dev"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    REDIS_URL: str = "redis://localhost:6379/0"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minio_admin"
    MINIO_SECRET_KEY: str = "minio_password"
    MINIO_BUCKET_MEDIA: str = "koptumbuh-media"
    MINIO_BUCKET_EXPORTS: str = "koptumbuh-exports"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    WHATSAPP_VERIFY_TOKEN: str = ""
    EVOLUTION_API_URL: str = "http://evolution:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "koptumbuh"
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: list = ["http://localhost:3000"]
    RATE_LIMIT_WEBHOOK: str = "60/minute"
    MAX_TEXT_LENGTH: int = 4000
    MAX_AUDIO_SECONDS: int = 60
    MAX_MEDIA_SIZE_MB: int = 10

    class Config:
        env_file = ".env"

settings = Settings()
```

### 1f. .env.example

```bash
# Database
DATABASE_URL=postgresql+asyncpg://dev_admin:devpassword@localhost:5432/koptumbuh_dev
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO (S3-compatible storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=minio_password
MINIO_BUCKET_MEDIA=koptumbuh-media
MINIO_BUCKET_EXPORTS=koptumbuh-exports

# Google Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# Evolution API (WhatsApp via Baileys — self-hosted, no Meta token expiry)
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_API_KEY=koptumbuh-evolution-key
EVOLUTION_INSTANCE=koptumbuh
WHATSAPP_VERIFY_TOKEN=koptumbuh_webhook_secret

# JWT
JWT_SECRET_KEY=generate-a-random-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Rate Limiting
RATE_LIMIT_WEBHOOK=60/minute

# Input Bounds
MAX_TEXT_LENGTH=4000
MAX_AUDIO_SECONDS=60
MAX_MEDIA_SIZE_MB=10
```

### 1g. SQLAlchemy Models

Map all 40 tables. Key pattern — everything lives in `koptumbuh` schema, everything FKs to `referensi_koperasi_wilayah`:

```python
# app/models/core.py
from sqlalchemy import Column, String, Integer, Numeric, Date, TIMESTAMP, Text, Boolean, ForeignKey, CheckConstraint, SmallInteger, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base
import uuid

class ReferensiWilayah(Base):
    __tablename__ = "referensi_wilayah"
    __table_args__ = {"schema": "koptumbuh"}
    kode_wilayah = Column(String, primary_key=True)
    provinsi = Column(String)
    kab_kota = Column(String)
    kecamatan = Column(String)
    desa_kelurahan = Column(String)
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

class ReferensiKoperasiWilayah(Base):
    """CENTRAL HUB — all child tables FK here, not directly to profil_koperasi."""
    __tablename__ = "referensi_koperasi_wilayah"
    __table_args__ = {"schema": "koptumbuh"}
    koperasi_ref = Column(String, primary_key=True)
    kode_wilayah = Column(String, ForeignKey("koptumbuh.referensi_wilayah.kode_wilayah"))
    dibuat_pada = Column(TIMESTAMP(timezone=True))
    diperbarui_pada = Column(TIMESTAMP(timezone=True))

# ... (all 40 tables mapped — 7 model files covering the groups)
```

---

## Phase 2: WhatsApp Ingestion & Async Pipeline (Hours 6–16)

### Phase 2 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 2.1 | 2 hr | Webhook endpoint (Evolution API receiver) | Phase 1 complete | `POST /webhooks/whatsapp` returns 200, writes to pesan_masuk | curl smoke test → pesan_masuk row created |
| 2.2 | 1 hr | Idempotency + rate limiting + sender resolution | 2.1 | Redis lock + DB UNIQUE constraint working | Send same message_id twice → second returns `"duplicate"` |
| 2.3 | 1.5 hr | Celery app + Beat configuration + message router | 2.1 | `process_message` task chains working | Celery worker picks up job, logs show chain execution |
| 2.4 | 1 hr | Media download worker (Evolution API + MinIO) | 2.3 | Audio/images downloaded → MinIO → ffprobe duration check | Upload test file, verify in MinIO console |
| 2.5 | 2 hr | Gemini AI service (text + audio + image) | 2.3 | `ai_service.py` — parse_text, transcribe_audio, ocr_receipt | Unit test each function with mock Gemini response |
| 2.6 | 1.5 hr | Validation worker (entity resolution + DB math) | 2.5 | Unrecognized products → NEEDS_REVIEW; matched → VALID with DB prices | Send text → verify parsing_pesan has resolved_items with db_price |
| 2.7 | 1 hr | WhatsApp outbound dispatcher + confirmation template | 2.6 | Confirmation message formatted and sent via Evolution API | Check notifikasi_log for SENT status |
| 2.8 | 30 min | Dev-mode confirmation bypass endpoint | 2.6 | `POST /dev/simulate-confirmation` works | Send YA → verify transaction committed |

### 2a. Webhook Endpoint

```python
# app/api/v1/webhooks.py
from fastapi import APIRouter, Request, Response, HTTPException
from app.config import settings
from app.database import get_db
from app.utils.idempotency import check_idempotency

router = APIRouter(tags=["webhook"])

@router.get("/webhooks/whatsapp")
async def verify_webhook(request: Request):
    """WhatsApp verification challenge."""
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verify token")

@router.post("/webhooks/whatsapp")
async def receive_whatsapp(payload: dict):
    """
    Evolution API webhook receiver.
    
    Evolution POSTs:
    {
      "event": "messages.upsert",
      "data": {
        "key": {"id": "wamid.ABC123", "remoteJid": "628123456003@s.whatsapp.net"},
        "message": {
          "conversation": "Bu Siti beli 2 Beras 5kg",
          "messageType": "conversation" | "audioMessage" | "imageMessage"
        }
      }
    }
    
    Flow:
    1. Extract message_id (idempotency key), sender phone, type, content
    2. Rate limit check (Redis token bucket — NOT in-memory)
    3. Resolve sender phone → pengguna_id + koperasi_ref
    4. Idempotency: Redis lock + DB UNIQUE constraint
    5. INSERT pesan_masuk (status=RECEIVED)
    6. Push to Celery queue
    7. Return 200 OK within 500ms
    """
    # Ignore non-message events (status updates, receipts, etc.)
    if payload.get("event") != "messages.upsert":
        return {"status": "ignored"}

    data = payload["data"]
    message_id = data["key"]["id"]
    sender_raw = data["key"]["remoteJid"]  # "628123456003@s.whatsapp.net"
    sender_phone = sender_raw.split("@")[0]
    msg = data.get("message", {})

    # Classify input type from Evolution messageType
    msg_type = msg.get("messageType", "conversation")
    if msg_type == "conversation":
        input_type = "TEXT"
        content = msg.get("conversation", "")
    elif "audio" in msg_type:
        input_type = "VOICE"
        content = None  # Downloaded by worker via Evolution API
    elif "image" in msg_type:
        input_type = "PHOTO"
        content = None
    else:
        input_type = "DOCUMENT"
        content = None

    # 1. Rate limit — MUST use Redis INCR + EXPIRE (token bucket).
    #    DO NOT use in-memory rate limiting — multiple Uvicorn workers
    #    each have their own memory, so limits won't aggregate.
    if not rate_limiter.check(sender_phone):
        return {"status": "rate_limited"}

    # 2. Resolve user
    user = await resolve_user_by_phone(sender_phone)
    if not user:
        return {"status": "unknown_user"}

    # 3. Validate bounds (text length + media size only at webhook level).
    #    NOTE: Audio DURATION cannot be checked here — WhatsApp payload
    #    only provides a media ID, not duration in seconds. Duration is
    #    enforced in the download_media worker using ffprobe.
    validate_input_bounds(content, msg)

    # 4. Idempotency — Redis lock first (fast), DB UNIQUE constraint second (authoritative)
    lock_key = f"lock:wa:{message_id}"
    if not redis_client.set(lock_key, "processing", ex=30, nx=True):
        return {"status": "duplicate"}

    # 5. Write to pesan_masuk
    pesan = PesanMasuk(
        koperasi_ref=user.koperasi_ref,
        pengguna_id=user.pengguna_id,
        whatsapp_message_id=message_id,
        input_type=input_type,
        raw_text=content,
        media_url=None,  # Evolution API media downloaded directly in worker
        status="RECEIVED"
    )
    db.add(pesan)
    await db.commit()
    await db.refresh(pesan)

    # 6. Push to Celery
    process_message.delay(str(pesan.pesan_id))

    # 7. Return immediately
    return {"success": True, "data": {"status": "queued", "pesan_id": str(pesan.pesan_id)}}
```

### 2b. Idempotency Strategy

Two-layer defense:
1. **Redis SETNX** — fast, distributed, prevents race conditions within the 30s lock window
2. **PostgreSQL UNIQUE constraint** on `pesan_masuk.whatsapp_message_id` — authoritative, permanent

If Redis is down, the UNIQUE constraint still catches duplicates. Catch `IntegrityError` and return friendly duplicate response.

### 2c. Celery Configuration + Beat Schedule

```python
# app/workers/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery("koptumbuh", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,     # 5 min soft limit
    task_time_limit=600,          # 10 min hard limit
    worker_max_tasks_per_child=100,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "generate-recommendations": {
        "task": "app.workers.recommendations.generate_all_recommendations",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
    },
    "cleanup-expired-sessions": {
        "task": "app.workers.cleanup.cleanup_expired_sessions",
        "schedule": crontab(minute=30, hour="*/1"),  # Every hour at :30
    },
}

# app/workers/celery_beat.py — separate process
# Run with: celery -A app.workers.celery_app beat --loglevel=info
```

### 2d. Message Pipeline with Error Handling

```python
# app/workers/router.py
from celery import chain, group
from app.workers.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_message(self, pesan_id: str):
    """
    Orchestrates the full pipeline. Each step is a Celery task — if one fails,
    only that step retries, not the whole chain.
    
    Flow: route → [audio|vision|text] → parse → validate → dispatch
    """
    pesan = get_pesan_sync(pesan_id)
    pesan.status = "PROCESSING"
    db.commit()

    try:
        match pesan.input_type:
            case "TEXT":
                # Text → parse directly
                chain(
                    parse_text.s(pesan_id, pesan.raw_text),
                    validate_parsing.s(),
                    dispatch_confirmation.s()
                ).apply_async()
            case "VOICE":
                # Audio → download media → Gemini transcription → parse → validate → dispatch
                chain(
                    download_media.s(pesan_id, pesan.media_url),
                    transcribe_audio.s(),
                    parse_text.s(),
                    validate_parsing.s(),
                    dispatch_confirmation.s()
                ).apply_async()
            case "PHOTO":
                # Image → download media → Vision OCR → parse → validate → dispatch
                chain(
                    download_media.s(pesan_id, pesan.media_url),
                    ocr_image.s(),
                    validate_parsing.s(),  # Vision returns structured JSON directly
                    dispatch_confirmation.s()
                ).apply_async()
            case "DOCUMENT":
                # Try as image first, fall back to unsupported
                chain(
                    download_media.s(pesan_id, pesan.media_url),
                    ocr_image.s(),
                    validate_parsing.s(),
                    dispatch_confirmation.s()
                ).apply_async()
    except Exception as exc:
        pesan.status = "FAILED"
        db.commit()
        self.retry(exc=exc, countdown=60)
```

### 2e. Media Download Worker

```python
# app/workers/router.py (continued)

@celery_app.task(bind=True, max_retries=2)
def download_media(self, pesan_id: str, message_id: str) -> dict:
    """Download media from Evolution API, enforce audio duration, upload to MinIO."""
    # Fetch media via Evolution API (base64-encoded in response)
    content_bytes, content_type = whatsapp_service.download_media(message_id)

    # Audio duration enforcement (cannot be done at webhook — WhatsApp
    # only sends a media ID, not duration). Use ffprobe to probe.
    if "audio" in content_type:
        import subprocess, tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            f.write(content_bytes)
            tmp = f.name
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", tmp],
                capture_output=True, text=True, timeout=10
            )
            duration = float(result.stdout.strip())
            if duration > settings.MAX_AUDIO_SECONDS:
                update_pesan_status(pesan_id, "FAILED")
                return {"error": f"Audio terlalu panjang ({duration:.0f}s). Maksimum {settings.MAX_AUDIO_SECONDS}s."}
        finally:
            os.unlink(tmp)

    # Upload to MinIO
    object_key = f"{pesan_id}/{uuid.uuid4().hex}.{get_extension(content_type)}"
    minio_client.put_object(
        settings.MINIO_BUCKET_MEDIA, object_key,
        content_bytes, len(content_bytes),
        content_type=content_type
    )

    return {
        "pesan_id": pesan_id,
        "minio_key": object_key,
        "media_data": response.content,
        "content_type": response.headers["content-type"]
    }
```

### 2f. AI Service (Google Gemini Integration)

Gemini 2.5 Flash is a single multimodal model that handles text, images, and audio — no separate Whisper or Vision endpoints needed.

```python
# app/services/ai_service.py
import json, base64, tempfile, os
from google import genai
from google.genai import types
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Response schema for structured extraction (Gemini controlled generation)
EXTRACTION_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=1000,
    response_mime_type="application/json",
    response_schema=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "intent": types.Schema(
                type=types.Type.STRING,
                enum=["RECORD_SALE", "RECORD_RECEIPT", "ADJUST_STOCK", "ASK_KNOWLEDGE", "UNRESOLVED"]
            ),
            "customer_name": types.Schema(type=types.Type.STRING),
            "payment_method": types.Schema(
                type=types.Type.STRING,
                enum=["Cash", "Transfer", "Lainnya"]
            ),
            "line_items": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "product_name": types.Schema(type=types.Type.STRING),
                        "quantity": types.Schema(type=types.Type.NUMBER),
                        "unit": types.Schema(type=types.Type.STRING),
                    },
                    required=["product_name", "quantity", "unit"]
                )
            ),
            "confidence_score": types.Schema(type=types.Type.NUMBER),
        },
        required=["intent", "customer_name", "line_items", "confidence_score"]
    ),
    system_instruction=(
        "Anda adalah parser transaksi koperasi Indonesia. Ekstrak produk, jumlah, "
        "nama pelanggan, dan metode pembayaran. JANGAN menghitung total — hanya ekstrak "
        "apa yang disebutkan secara eksplisit. Bahasa Indonesia."
    )
)

EXTRACTION_CONFIG_IMAGE = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=1000,
    response_mime_type="application/json",
    response_schema=EXTRACTION_CONFIG.response_schema,  # Same schema
    system_instruction=(
        "Ekstrak SEMUA produk, jumlah, dan harga yang terlihat di foto ini. "
        "JANGAN menghitung total. Bahasa Indonesia."
    )
)


async def parse_text_to_json(text: str) -> dict:
    """Gemini 2.5 Flash — structured extraction from text."""
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,  # "gemini-2.5-flash"
        contents=text,
        config=EXTRACTION_CONFIG,
    )
    return json.loads(response.text)


async def transcribe_audio(audio_bytes: bytes, mime_type: str) -> str:
    """Gemini 2.5 Flash — native audio transcription (no separate Whisper call)."""
    # Gemini accepts audio bytes directly — transcribe and parse in ONE call.
    # For transcription-only (before parsing), we ask for plain text.
    config = types.GenerateContentConfig(
        temperature=0.0,
        system_instruction="Transkripsikan audio ini ke teks Bahasa Indonesia. Jangan tambahkan apapun selain hasil transkripsi."
    )
    part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[part],
        config=config,
    )
    return response.text


async def ocr_receipt(image_bytes: bytes, mime_type: str) -> dict:
    """Gemini 2.5 Flash — native multimodal: image → structured JSON."""
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[part, "Ekstrak semua item yang terlihat."],
        config=EXTRACTION_CONFIG_IMAGE,
    )
    return json.loads(response.text)
```

**AI configuration decisions:**
- `temperature=0.0` — deterministic extraction, no creativity
- `response_mime_type="application/json"` — Gemini enforces structured output matching the schema
- Single model for all three modes (text, image, audio) — simplifies the stack
- "JANGAN menghitung total" — enforced in every system instruction
- Indonesian language in system instructions — Gemini handles Indonesian natively

#### Knowledge Q&A — AI FAQ Assistant (Touchpoint 4)

Members and operators ask operational questions via WhatsApp. Gemini answers from `artikel_pengetahuan` using the existing GIN full-text search index. This is NOT an open chatbot — it's restricted to the knowledge base.

```
Member: "Bagaimana cara daftar anggota baru?"
→ GIN search: to_tsvector('simple', 'daftar anggota baru')
→ Top 3 matching articles found
→ Gemini: "Untuk mendaftar anggota baru: 1) Buka menu Anggota 2) Klik Tambah..."
→ WhatsApp reply sent
```

```python
# app/services/ai_service.py

KNOWLEDGE_QA_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=500,
    system_instruction=(
        "Anda adalah asisten Koperasi Merah Putih. Jawab pertanyaan anggota "
        "berdasarkan artikel pengetahuan yang diberikan. Jika jawaban tidak "
        "ada di artikel, katakan: 'Maaf, saya tidak menemukan informasi tentang '
        "itu. Silakan hubungi pengurus koperasi.' JANGAN mengarang jawaban. "
        "Gunakan Bahasa Indonesia yang ramah dan mudah dipahami."
    )
)

async def answer_knowledge_question(question: str, koperasi_ref: str) -> str:
    """Search artikel_pengetahuan via GIN index, feed top results to Gemini for answer."""
    # GIN full-text search (index already exists from canonical schema)
    results = await db.execute(
        select(ArtikelPengetahuan)
        .where(ArtikelPengetahuan.koperasi_ref == koperasi_ref)
        .where(func.to_tsvector('simple', ArtikelPengetahuan.judul + ' ' + ArtikelPengetahuan.isi)
               .match(question, postgresql_regconfig='simple'))
        .order_by(func.ts_rank(
            func.to_tsvector('simple', ArtikelPengetahuan.judul + ' ' + ArtikelPengetahuan.isi),
            func.plainto_tsquery('simple', question)
        ).desc())
        .limit(3)
    )
    articles = results.scalars().all()

    if not articles:
        return "Maaf, saya tidak menemukan informasi tentang pertanyaan Anda. Silakan hubungi pengurus koperasi."

    context = "\n\n".join([f"ARTIKEL: {a.judul}\n{a.isi}" for a in articles])

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=[
            f"Pertanyaan anggota: {question}\n\nArtikel pengetahuan yang relevan:\n{context}"
        ],
        config=KNOWLEDGE_QA_CONFIG
    )
    return response.text
```

**Route in message handler:**
```python
match detected_intent:
    case "ASK_KNOWLEDGE":
        answer = await answer_knowledge_question(text, koperasi_ref)
        await send_whatsapp_message(user.phone, answer)
```

#### Recommendation Narrative (Touchpoint 5)

Engine output is raw data (stock=12, ads=6, lead_time=3). Gemini turns it into conversational Indonesian that operators and members understand.

```python
NARRATIVE_CONFIG = types.GenerateContentConfig(
    temperature=0.3,  # Slight creativity for natural phrasing
    max_output_tokens=200,
    system_instruction=(
        "Anda adalah asisten koperasi yang menjelaskan rekomendasi dalam Bahasa "
        "Indonesia yang singkat dan mudah dipahami operator desa. Gunakan kalimat "
        "pendek. Sebutkan angka spesifik. Akhiri dengan saran tindakan."
    )
)

async def generate_recommendation_narrative(rec: Rekomendasi) -> str:
    """Turn raw engine output into human-readable recommendation text."""
    data = rec.explanation_payload  # JSONB: {current_stock, avg_daily_sales, lead_time, ...}

    prompt = f"""
    Jenis rekomendasi: {rec.jenis}
    Produk: {rec.judul}
    Data: stok={data.get('current_stock')}, terjual={data.get('avg_daily_sales')}/hari,
           lead_time={data.get('lead_time_days')} hari

    Tulis rekomendasi 1-2 kalimat dalam Bahasa Indonesia.
    """
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=NARRATIVE_CONFIG
    )
    return response.text
```

**Example output:**
> "Stok Telur Ayam 1kg tinggal 12 butir. Rata-rata terjual 6 butir per hari, dan supplier butuh 3 hari untuk kirim. Disarankan segera pesan 18 butir sebelum stok habis dalam 2 hari."

#### SHU Explanation (Touchpoint 6)

When a member asks "SHU saya?", the formula provides the number. Gemini provides the explanation.

```python
SHU_EXPLAIN_CONFIG = types.GenerateContentConfig(
    temperature=0.0,
    max_output_tokens=300,
    system_instruction=(
        "Anda menjelaskan SHU (Sisa Hasil Usaha) koperasi kepada anggota dalam "
        "Bahasa Indonesia yang mudah dipahami. Gunakan data yang diberikan. "
        "Jelaskan mengapa SHU naik/turun. Dorong anggota untuk lebih aktif berbelanja."
    )
)

async def explain_shu(anggota_ref: str) -> str:
    """Generate personalized SHU explanation for a member."""
    shu_data = get_shu_projection(anggota_ref)  # from v_shu_estimasi query

    prompt = f"""
    Anggota: {shu_data['nama']}
    Total belanja tahun ini: Rp {shu_data['total_belanja']:,}
    Estimasi SHU: Rp {shu_data['estimasi_shu']:,}
    Jumlah transaksi: {shu_data['jumlah_transaksi']}
    Margin SHU koperasi: {shu_data['margin_persen']}%
    Bulan lalu: {shu_data['belanja_bulan_lalu']:,}, Bulan ini: {shu_data['belanja_bulan_ini']:,}

    Jelaskan SHU-nya dalam 2-3 kalimat.
    """
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=SHU_EXPLAIN_CONFIG
    )
    return response.text
```

**Example output:**
> "Total belanja Anda tahun ini Rp 3.450.000 dengan estimasi SHU Rp 172.500. Belanja bulan ini naik 15% dibanding bulan lalu — pertahankan! Semakin banyak belanja di koperasi, semakin besar SHU yang Anda terima akhir tahun."

### 2g. Validation Worker (Entity Resolution + No AI Math)

```python
# app/workers/validator.py

@celery_app.task(bind=True, max_retries=2)
def validate_parsing(self, parsing_result: dict) -> dict:
    """
    THE CRITICAL WORKER. Enforces the "No AI Math" rule.
    
    1. Entity resolution: fuzzy match product names → produk_sample_id
       fuzzy match customer names → anggota_ref / pelanggan_id
    2. Deterministic math: harga_jual from DB × quantity = subtotal
       DISREGARD any AI-computed totals entirely
    3. If all items resolved: status = VALID, set Redis → AWAITING_CONFIRMATION
       If any unresolved: status = INVALID, send error message to user
    """
    parsing = get_parsing(parsing_result["parsing_id"])
    koperasi_ref = parsing.koperasi_ref
    payload = parsing.extracted_payload
    errors = []
    resolved_items = []

    for item in payload["line_items"]:
        # Entity resolution pipeline: exact → ILIKE → word-overlap
        product = resolve_product(item["product_name"], koperasi_ref)
        if not product:
            errors.append({"item": item["product_name"], "error": "PRODUCT_NOT_FOUND"})
            continue

        # DATABASE PRICE — never trust AI price
        db_price = float(product.harga_jual)
        resolved_items.append({
            "produk_sample_id": product.produk_sample_id,
            "nama_produk": product.nama_produk,
            "quantity": item["quantity"],
            "unit_price": db_price,
            "subtotal": item["quantity"] * db_price  # DATABASE MATH
        })

    # Resolve customer
    customer = resolve_customer(payload.get("customer_name"), koperasi_ref)

    calculated_total = sum(ri["subtotal"] for ri in resolved_items)

    # Update parsing record
    parsing.extracted_payload = {
        **payload,
        "resolved_items": resolved_items,
        "calculated_total": calculated_total,
        "customer_ref": customer.anggota_ref if customer else None,
        "customer_id": str(customer.pelanggan_id) if customer and hasattr(customer, 'pelanggan_id') else None
    }
    parsing.validation_errors = errors
    parsing.status = "VALID" if not errors else "INVALID"
    parsing.confidence_score = payload.get("confidence_score", 0.0)
    db.commit()

    # Update pesan status
    pesan = parsing.pesan
    pesan.status = "PARSED" if parsing.status == "VALID" else "NEEDS_REVIEW"
    pesan.processed_at = func.now()
    db.commit()

    return {"parsing_id": str(parsing.parsing_id), "status": parsing.status}
```

**Entity resolution strategy:**
1. Exact match on `nama_produk` (fastest, most common)
2. `ILIKE '%keyword%'` (handles "Beras 5kg" vs "Beras Premium 5kg")
3. Word overlap / Jaccard similarity (handles reordered words)
4. If no match → flag NEEDS_REVIEW, user receives error with closest suggestions

### 2h. Outbound Dispatcher

```python
# app/workers/dispatcher.py

@celery_app.task(bind=True, max_retries=3)
def dispatch_confirmation(self, validation_result: dict):
    """Format and send WhatsApp confirmation or error message."""
    parsing_id = validation_result["parsing_id"]
    parsing = get_parsing(parsing_id)

    if validation_result["status"] == "VALID":
        # Set Redis session state
        user = parsing.pesan.pengguna
        redis_client.setex(
            f"session:{user.nomor_whatsapp}",
            900,  # 15-minute TTL
            json.dumps({"state": "AWAITING_CONFIRMATION", "parsing_id": parsing_id})
        )
        message = format_confirmation_message(parsing)
    else:
        # Send error with suggestions
        message = format_error_message(parsing)

    # Send via WhatsApp API
    result = whatsapp_service.send_message(to=user.nomor_whatsapp, body=message)

    # Log to notifikasi_log
    notifikasi = NotifikasiLog(
        koperasi_ref=parsing.koperasi_ref,
        pengguna_id=parsing.pesan.pengguna_id,
        channel="WHATSAPP",
        message_type="CONFIRMATION" if validation_result["status"] == "VALID" else "ALERT",
        content=message,
        provider_message_id=result.get("message_id"),
        status="SENT" if result.get("success") else "FAILED",
        sent_at=func.now()
    )
    db.add(notifikasi)
    db.commit()

def format_confirmation_message(parsing) -> str:
    """Format the WhatsApp confirmation template."""
    payload = parsing.extracted_payload
    lines = []
    for i, item in enumerate(payload["resolved_items"]):
        lines.append(f"{i+1}. {item['nama_produk']}  {item['quantity']} × Rp {item['unit_price']:,.0f} = Rp {item['subtotal']:,.0f}")

    return (
        f"\U0001F4CB *Konfirmasi Transaksi*\n"
        f"Koperasi Tumbuh Bersama\n\n"
        f"Pelanggan: {payload.get('customer_name', '-')}\n"
        f"Bayar: {payload.get('payment_method', 'Cash')}\n\n"
        + "\n".join(lines) +
        f"\n{'─' * 30}\n"
        f"*Total: Rp {payload['calculated_total']:,.0f}*\n\n"
        f"Balas:\n"
        f"✅ *YA* — Simpan\n"
        f"✏️ *UBAH* — Koreksi & kirim ulang\n"
        f"❌ *BATAL* — Batalkan"
    )
```

### 2i. WhatsApp Service (Evolution API)

Evolution API is a self-hosted Docker container that uses the WhatsApp Web protocol (Baileys library). It eliminates Meta token expiry — one QR scan pairs your number, and the session persists.

```python
# app/services/whatsapp_service.py
import httpx
from app.config import settings

class WhatsAppService:
    """Wrapper around Evolution API — swap to Meta Cloud API later without changing any callers."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

    async def send_message(self, to: str, body: str) -> dict:
        """Send a text message via Evolution API."""
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key, "Content-Type": "application/json"},
                json={"number": to, "text": body}
            )
            if response.status_code in (200, 201):
                data = response.json()
                return {"success": True, "message_id": data.get("key", {}).get("id", "")}
            return {"success": False, "error": response.text}

    async def download_media(self, message_id: str) -> bytes:
        """Download media file for a given message."""
        async with httpx.AsyncClient(timeout=30) as client:
            # Evolution API serves media at /chat/getMedia/{instance}
            response = await client.post(
                f"{self.base_url}/chat/getMedia/{self.instance}",
                headers={"apikey": self.api_key},
                json={"message": {"key": {"id": message_id}}}
            )
            response.raise_for_status()
            data = response.json()
            # Media is base64-encoded in the response
            return base64.b64decode(data.get("media", ""))

    # --- Webhook format ---
    # Evolution API POSTs to our /webhooks/whatsapp with this payload:
    # {
    #   "event": "messages.upsert",
    #   "data": {
    #     "key": {
    #       "id": "ABCD1234",           ← our idempotency key
    #       "remoteJid": "628123456003@s.whatsapp.net"
    #     },
    #     "message": {
    #       "conversation": "Bu Siti beli 2 Beras 5kg",  ← text content
    #       "messageType": "conversation" | "audioMessage" | "imageMessage"
    #     }
    #   }
    # }
```

---

## Phase 3: Confirmation Flow & Transaction Commit (Hours 16–24)

### Phase 3 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 3.1 | 1.5 hr | State machine handler (YA/UBAH/BATAL router) | Phase 2 complete | `state_machine.py` routes replies correctly | Send YA via dev endpoint → commit_transaction called |
| 3.2 | 2 hr | Atomic transaction commit (YA handler) | 3.1 | INSERT transaksi + barang_keluar + UPDATE inventaris in one TX | Verify: `SELECT total_pembayaran FROM transaksi_penjualan` matches DB-calculated total |
| 3.3 | 1 hr | UBAH handler (supersede + cache clear + re-prompt) | 3.1 | Old parsing → SUPERSEDED, Redis cleared, user gets re-send prompt | Verify no transaction created, parsing.status = 'SUPERSEDED' |
| 3.4 | 30 min | BATAL handler (cache clear + cancel message) | 3.1 | pesan_masuk.status = 'CANCELLED', Redis cleared | Verify no transaction, status is CANCELLED |
| 3.5 | 1 hr | Double-commit prevention (Redis + DB isolation) | 3.2 | Concurrent YA → only one commits | Send two YA replies rapidly → only 1 transaction created |
| 3.6 | 1 hr | End-to-end flow: webhook → AI → confirm → commit | 3.4 | Full happy path working | TC-003: transaksi + barang_keluar + inventaris all correct |
| 3.7 | 1 hr | Mobile polling endpoint for confirmation status | 3.6 | `GET /mobile/messages?status=PARSED` returns pending confirmations | Poll during flow → see status change from RECEIVED → PARSED → CONFIRMED |

### 3a. State Machine

```
IDLE → (message parsed) → AWAITING_CONFIRMATION (Redis, TTL 15 min)
     → YA  → COMMIT (atomic DB transaction) → IDLE
     → UBAH → CANCEL draft, reset session → IDLE (user re-sends)
     → BATAL → CANCEL → IDLE

Expired session (TTL elapsed): User re-sends message, treated as new.
```

### 3b. Confirmation Handler

```python
# app/services/state_machine.py

async def handle_confirmation_reply(pesan: PesanMasuk):
    """Detect and handle YA/UBAH/BATAL replies to pending confirmations."""
    reply = pesan.raw_text.strip().upper()

    # Check for active confirmation session
    user = pesan.pengguna
    session_data = redis_client.get(f"session:{user.nomor_whatsapp}")
    if not session_data:
        # No active session — treat as a new message → route to parser
        return route_and_extract_sync(str(pesan.pesan_id))

    session = json.loads(session_data)
    parsing = get_parsing(session["parsing_id"])

    match reply:
        case "YA":
            await commit_transaction_atomic(parsing, pesan)
            redis_client.delete(f"session:{user.nomor_whatsapp}")

        case "UBAH":
            parsing.status = "SUPERSEDED"
            db.commit()
            redis_client.delete(f"session:{user.nomor_whatsapp}")
            await send_message(user.nomor_whatsapp,
                "Draf dibatalkan. Silakan kirim ulang pesan dengan format yang benar.")

        case "BATAL":
            pesan.status = "CANCELLED"
            db.commit()
            redis_client.delete(f"session:{user.nomor_whatsapp}")
            await send_message(user.nomor_whatsapp,
                "❌ Transaksi dibatalkan. Tidak ada data yang disimpan.")

        case _:
            # Not YA/UBAH/BATAL — treat as new message
            return route_and_extract_sync(str(pesan.pesan_id))
```

### 3c. Atomic Transaction Commit (YA Handler)

```python
# app/workers/confirmer.py

async def commit_transaction_atomic(parsing: ParsingPesan, pesan: PesanMasuk):
    """Single PostgreSQL transaction — all or nothing."""
    payload = parsing.extracted_payload
    koperasi_ref = parsing.koperasi_ref

    async with db.begin() as tx:
        # 1. INSERT transaksi_penjualan
        tx_id = f"TRX-{datetime.now():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
        await tx.execute(
            insert(TransaksiPenjualan).values(
                transaksi_sample_id=tx_id,
                koperasi_ref=koperasi_ref,
                nama_pelanggan=payload["customer_name"],
                tanggal_dibuat=func.now(),
                total_pembayaran=payload["calculated_total"],
                status_transaksi="Paid",
                metode_pembayaran=payload.get("payment_method", "Cash")
            )
        )

        # 2. INSERT barang_keluar_produk (line items) + UPDATE inventaris_produk
        for item in payload["resolved_items"]:
            await tx.execute(
                insert(BarangKeluarProduk).values(
                    transaksi_sample_id=tx_id,
                    produk_sample_id=item["produk_sample_id"],
                    koperasi_ref=koperasi_ref,
                    jumlah_keluar=item["quantity"],
                    harga=item["unit_price"],
                    total_nilai=item["subtotal"],
                    nama_produk=item["nama_produk"],
                    status_transaksi="Paid"
                )
            )

            # Decrement inventory
            await tx.execute(
                update(InventarisProduk)
                .where(InventarisProduk.koperasi_ref == koperasi_ref)
                .where(InventarisProduk.produk_sample_id == item["produk_sample_id"])
                .values(stok=InventarisProduk.stok - item["quantity"])
            )

        # 3. INSERT relasi_transaksi_pihak
        if payload.get("customer_ref"):  # Known member
            await tx.execute(
                insert(RelasiTransaksiPihak).values(
                    transaksi_sample_id=tx_id,
                    anggota_ref=payload["customer_ref"],
                    relationship_type="MEMBER_CUSTOMER",
                    match_method="ai_parsed"
                )
            )
        elif payload.get("customer_id"):  # Registered walk-in
            await tx.execute(
                insert(RelasiTransaksiPihak).values(
                    transaksi_sample_id=tx_id,
                    pelanggan_id=payload["customer_id"],
                    relationship_type="NON_MEMBER_CUSTOMER",
                    match_method="ai_parsed"
                )
            )

        # 4. INSERT konfirmasi_pengguna
        await tx.execute(
            insert(KonfirmasiPengguna).values(
                pesan_id=pesan.pesan_id,
                parsing_id=parsing.parsing_id,
                pengguna_id=pesan.pengguna_id,
                keputusan="YA",
                confirmed_at=func.now()
            )
        )

        # 5. UPDATE parsing + pesan status
        await tx.execute(
            update(ParsingPesan).where(ParsingPesan.parsing_id == parsing.parsing_id)
            .values(status="VALID")
        )
        await tx.execute(
            update(PesanMasuk).where(PesanMasuk.pesan_id == pesan.pesan_id)
            .values(status="CONFIRMED")
        )

    # Outside transaction — send success notification
    await send_message(
        pesan.pengguna.nomor_whatsapp,
        f"✅ Transaksi berhasil disimpan!\nID: {tx_id}\nTotal: Rp {payload['calculated_total']:,.0f}"
    )
```

**Double-commit prevention**: Redis session is deleted BEFORE processing YA (in the handler). If a second YA arrives, the session is gone → treated as a new message. DB transaction isolation prevents the edge case where two YAs slip through.

---

## Phase 4: Web Dashboard (Hours 24–34)

### Phase 4 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 4.1 | 30 min | Next.js project init + package.json + Tailwind + shadcn/ui | Phase 3 API running | `npm run dev` → Next.js at :3000 | Open http://localhost:3000 → welcome page |
| 4.2 | 1 hr | Auth middleware + login page + JWT flow | 4.1 | Login → store token → redirect to dashboard | Login with demo credentials → redirected to / |
| 4.3 | 1 hr | API client with auto-refresh + standard error handling | 4.2 | `apiClient<T>()` generic function | Call any endpoint → typed response |
| 4.4 | 30 min | Dashboard layout shell (sidebar + header) | 4.2 | Navigation sidebar with all section links | Click each link → navigates to correct route |
| 4.5 | 1.5 hr | Dashboard home: KPI cards + sales chart + top products | 4.4 | 4 KPI cards + 2 Recharts components | Compare dashboard numbers against direct SQL queries |
| 4.6 | 2 hr | Analytics pages (sales trends, margin, slow-moving, active members, reconciliation) | 4.5 | 5 analytics sub-pages with charts + tables | Filter by date range → chart updates |
| 4.7 | 2.5 hr | Inventory pages (product list, detail, movements, adjustments, restock form) | 4.5 | 5 inventory pages with stock data | Record restock → inventory count increases |
| 4.8 | 2 hr | Supply chain pages (suppliers, supplier detail, restock plan, purchase orders, scorecard) | 4.5 | 5 supply chain pages | Restock plan shows correct suggested quantities |
| 4.9 | 1 hr | Cooperatives + members pages (detail tabs, segmentation, preferences) | 4.5 | Multi-tab cooperative detail + member pages | RFM segmentation shows correct tiers |
| 4.10 | 1 hr | Finance + village + knowledge + export pages | 4.5 | Remaining admin pages | All pages load without console errors |
| 4.11 | 1 hr | Settings + user management pages | 4.5 | Profile edit + user CRUD (Admin only) | Create new user → appears in user table |
| 4.12 | 30 min | Responsive check + cross-browser verification | 4.11 | Works at desktop + tablet widths | Resize browser → layout adapts correctly |

### Dashboard Component Patterns

All 30 pages use one of three layout patterns. Consistency reduces development time:

**Pattern 1: Dashboard Shell** (applied to 5 pages: home, analytics/*)
```
┌────────────────────────────────────────────┐
│ [Sidebar]  │  Header (user menu)           │
│            │───────────────────────────────│
│  Nav links │  KPI Cards Row                │
│            │  ┌─────┐ ┌─────┐ ┌─────┐     │
│            │  └─────┘ └─────┘ └─────┘     │
│            │  Chart 1 (full width)         │
│            │  ┌──────┐ ┌──────┐            │
│            │  │Chart2│ │Chart3│            │
│            │  └──────┘ └──────┘            │
└────────────────────────────────────────────┘
```

**Pattern 2: Data Table Page** (applied to 15 pages: inventory, supply-chain, members, etc.)
```
┌────────────────────────────────────────────┐
│ [Sidebar]  │  Page Title      [+ Action]  │
│            │───────────────────────────────│
│            │  [Search...] [Filters] [Date] │
│            │  ┌───────────────────────────┐│
│            │  │ DataTable (sortable)      ││
│            │  │ col1 | col2 | col3 | col4 ││
│            │  │ ... rows ...              ││
│            │  └───────────────────────────┘│
│            │  < 1 2 3 ... Pagination >    │
└────────────────────────────────────────────┘
```

**Pattern 3: Form Page** (applied to 5 pages: restock, manual entry, settings, etc.)
```
┌────────────────────────────────────────────┐
│ [Sidebar]  │  Form Title                   │
│            │───────────────────────────────│
│            │  ┌───────────────────────────┐│
│            │  │ Field 1: [_____________]  ││
│            │  │ Field 2: [_____________]  ││
│            │  │ Field 3: [▼ Select...  ]  ││
│            │  │                           ││
│            │  │ [Submit]  [Cancel]        ││
│            │  └───────────────────────────┘│
└────────────────────────────────────────────┘
```

### Web Dashboard package.json

```json
{
  "name": "koptumbuh-dashboard",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@tanstack/react-query": "^5.50.0",
    "@tanstack/react-table": "^8.20.0",
    "recharts": "^2.12.0",
    "date-fns": "^3.6.0",
    "lucide-react": "^0.400.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.4.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.57.0",
    "eslint-config-next": "^14.2.0",
    "shadcn-ui": "^0.9.0"
  }
}
```

### 4a. Next.js Auth Middleware

```typescript
// web-dashboard/middleware.ts
import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('koptumbuh_token')?.value;
  const { pathname } = request.nextUrl;

  // Public routes
  if (pathname.startsWith('/login')) {
    if (token) return NextResponse.redirect(new URL('/', request.url));
    return NextResponse.next();
  }

  // Protected routes
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

### 4b. API Client with Auto-Refresh

```typescript
// web-dashboard/lib/api.ts
import { getToken, setToken, clearToken } from './auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    // Try refresh
    const refreshToken = getToken('refresh');
    if (refreshToken) {
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (refreshRes.ok) {
        const { access_token, refresh_token } = (await refreshRes.json()).data;
        setToken(access_token, refresh_token);
        return apiClient(endpoint, options); // Retry
      }
    }
    clearToken();
    window.location.href = '/login';
  }

  if (!res.ok) {
    const error = await res.json();
    throw new ApiError(error.error.code, error.error.message, res.status);
  }

  return res.json();
}
```

### 4c. Standard API Response Handler

```typescript
// lib/api.ts (continued)
interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: { page: number; per_page: number; total: number; total_pages: number };
}

interface ApiErrorResponse {
  success: false;
  error: { code: string; message: string; details?: any };
}
```

### 4d. Web Dashboard Pages

| Route | Content |
|-------|---------|
| `/login` | JWT login form (phone + password) |
| `/` | KPI cards + sales trend chart + top products chart |
| `/analytics` | Date-range sales analytics, average basket, payment method breakdown, member activity |
| `/analytics/stock` | Reconciliation table: product, computed stock, snapshot, delta, status (MATCH/MISMATCH/SNAPSHOT_MISSING) |
| `/analytics/margin` | Profit margin per product: nominal margin, margin %, total profit contributed. From `v_margin_produk`. |
| `/analytics/slow-moving` | Slow-moving products: days without sales, status (BELUM_PERNAH_TERJUAL, 30+, 14-30). From `v_produk_lambat_bergerak`. |
| `/analytics/active-members` | Active member ranking: transactions, total spending, last active, activity status. From `v_anggota_aktif`. |
| `/analytics/shu` | Real-time SHU estimation chart — month-over-month, SHU margin trend |
| `/analytics/benchmark` | Compare cooperative metrics against sector averages (SHU margin, revenue per member) |
| `/analytics/revenue-breakdown` | Revenue by business unit (sembako, apotek, simpan_pinjam, etc.) |
| **INVENTORY** |
| `/inventory` | All products with stock levels, ⚠️ low stock indicators, search. Click → product detail. |
| `/inventory/[productId]` | Product detail: stock history chart (barang_masuk + barang_keluar timeline), current stock, supplier, price history |
| `/inventory/movements` | Combined stock movement log: barang_masuk + barang_keluar in one table. Filters: type, date range, product. |
| `/inventory/adjustments` | penyesuaian_stok audit trail: who adjusted, when, delta, reason, source message |
| `/inventory/restock` | Record incoming goods form (barang_masuk): select supplier, products, quantities, purchase prices → updates inventaris |
| **SUPPLY CHAIN** |
| `/supply-chain` | Supplier list with: name, contact, lead time, payment terms, products supplied, status badges |
| `/supply-chain/[id]` | Supplier detail: order history (barang_masuk from this supplier), average lead time, on-time %, products supplied |
| `/supply-chain/restock-plan` | All products needing restock: current stock, ADS, days remaining, suggested order qty, preferred supplier. Sort by urgency. |
| `/supply-chain/purchase-history` | All barang_masuk records: date, supplier, products, quantities, total cost. Filterable by supplier and date range. |
| `/supply-chain/supplier-scorecard` | Supplier comparison: on-time %, lead time actual vs promised, price trends |
| `/supply-chain/purchase-orders` | PO list: status (DRAFT, DIKIRIM, DITERIMA), supplier, dates, items ordered vs received |
| **COOPERATIVES** |
| `/cooperatives` | All cooperatives table (for pembina) |
| `/cooperatives/[ref]` | Cooperative detail with tabs: Profile, Board, Outlets, Assets, Documents, RAT, KBLI |
| `/cooperatives/[ref]/outlets` | Gerai list and management |
| `/cooperatives/[ref]/assets` | Aset list with progress bars |
| `/cooperatives/[ref]/documents` | Legal documents with expiry warnings |
| `/cooperatives/[ref]/rat` | RAT records — legally required view |
| `/members` | Cross-cooperative member search + table |
| `/members/[id]` | Member detail: profile, savings, transaction history, activity |
| `/members/segmentation` | RFM tier distribution chart + table — DIAMOND through TIDAK_AKTIF |
| **RAT & VILLAGE** |
| `/rat` | All RAT records: filter by status, year. SHU summary chart. |
| `/rat/[id]` | RAT detail viewer — parsed financial tables: Balance Sheet, Income Statement, Budget vs Actual |
| `/rat/compare` | Side-by-side RAT comparison or actual vs budget (RAPB) |
| `/rat/generate` | RAT report generator — select tahun_buku, click generate → downloads JSON |
| `/village` | Village economic potential ranking, population stats, dana desa distribution |
| `/village/[kode_wilayah]` | Single village detail: commodities, demographics, budget |
| **FINANCE** |
| `/finance` | Financial overview: bank accounts, capital, applications |
| `/finance/capital` | Modal records with amounts and sources |
| `/finance/applications` | All pengajuan_* tables in tabbed view |
| `/village` | Village commodity data + demographic profiles |
| `/knowledge` | Artikel CRUD with full-text search |
| `/export` | SIMKOPDES export form + history table + download links |
| `/settings` | Current user profile + change password |
| `/settings/users` | User management (Admin only) |
| **LOANS (PINJAMAN)** |
| `/loans` | All loans: filter by member, status (AKTIF, LUNAS, MACET). Table with amount, tenor, member name. |
| `/loans/[id]` | Single loan detail: payment schedule, remaining balance, member profile |
| `/loans/create` | Create new loan: select member, amount, tenor, interest rate |
| **EMPLOYEES (KARYAWAN)** |
| `/employees` | Employee list: name, position, phone, status. Search, filter. |
| `/employees/[id]` | Employee detail + edit form |
| **BANNERS** |
| `/banners` | Promotional banners: image upload, active/inactive toggle, order |
| **HELPDESK (PENGADUAN)** |
| `/helpdesk` | Member complaints: status filter (BARU, PROSES, SELESAI), date, member |
| `/helpdesk/[id]` | Complaint detail + response form |
| **WILAYAH EXPLORER** |
| `/wilayah` | Hierarchical region browser: Province → District → Subdistrict → Village. Population stats per level. |
| **PRINTER SETUP** |
| `/settings/printer` | Thermal receipt printer configuration |
| **POS (IN-STORE)** |
| `/pos` | Touchscreen POS: product grid, category/subsidy filters, cart, customer lookup, payment. For walk-in customers at the counter. |
| **DELIVERY** |
| `/delivery` | All deliveries: status (MENUNGGU, DIKIRIM, TIBA), courier, customer, date |
| `/delivery/[id]` | Delivery detail: items, address, courier, status timeline |
| `/delivery/track/[id]` | **Live map tracking**: courier GPS position, route, speed, ETA, status timeline |
| **SUBSIDIES** |
| `/products/subsidies` | Government-subsidized products list (Minyakita, LPG, etc.) |

### In-Store POS System — The Missing Parallel Workflow

WhatsApp is for remote/field recording. But when a customer stands at the counter, the kasir uses a **touchscreen POS** — not WhatsApp. SIMKOPDES has a full POS module. KopTumbuh must have one too.

**The dual-transaction model:**

```
CUSTOMER AT COUNTER                        CUSTOMER NOT AT COUNTER
─────────────────────                      ────────────────────────
Kasir opens POS screen                     Operator opens WhatsApp
  → Searches product catalog                 → Types transaction message
  → Taps products into cart                  → AI extracts entities
  → Selects customer from list               → YA confirmation
  → Taps "Bayar"                             → TX committed
  → Selects payment method
  → TX committed
```

**POS Dashboard Page** (`/pos`):

```
┌─────────────────────────────────────────────────────────────┐
│  POS Kasir — Koperasi Tumbuh Bersama                         │
│                                                              │
│  ┌─────────────────────────┐  ┌───────────────────────────┐ │
│  │ 🔍 Cari produk...       │  │ 🛒 Keranjang Belanja       │ │
│  │ [Semua] [Sembako] [Sub] │  │                           │ │
│  │                         │  │ Beras Premium 5kg          │ │
│  │ ┌───────┐ ┌───────┐    │  │ 2 × Rp 65.000 = Rp 130.000│ │
│  │ │Beras  │ │Minyak │    │  │ [-] [2] [+]               │ │
│  │ │5kg    │ │Goreng │    │  │                           │ │
│  │ │65.000 │ │28.000 │    │  │ Minyak Goreng 2L           │ │
│  │ └───────┘ └───────┘    │  │ 1 × Rp 28.000 = Rp 28.000 │ │
│  │ ┌───────┐ ┌───────┐    │  │ [-] [1] [+]               │ │
│  │ │Gula   │ │Telur  │    │  │                           │ │
│  │ │14.000  │ │27.000 │    │  │ ─────────────────────     │ │
│  │ └───────┘ └───────┘    │  │ Total: Rp 158.000          │ │
│  │                         │  │                           │ │
│  │ [1] [2] [3] ... [10]   │  │ Pelanggan: [Bu Siti ▼]   │ │
│  │                         │  │ Tipe: [Ambil di Tempat]   │ │
│  └─────────────────────────┘  │ Pembayaran: [Cash ▼]      │ │
│                                │                           │ │
│                                │ [💳 Bayar]  [🗑️ Batal]   │ │
│                                └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**POS API Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/pos/products` | Product grid with prices, stock, categories, subsidy flags |
| `POST /admin/pos/transactions` | Create in-store transaction (no AI — direct entry) |
| `GET /admin/pos/customers/search?q=` | Quick customer lookup for cart |

### Delivery & Courier System

SIMKOPDES has a full logistics workflow: warehouse confirms stock → admin logistik assigns courier → kurir delivers → marked arrived. KopTumbuh adds tracking.

**Dashboard Pages:**

| Route | Content |
|-------|---------|
| `/delivery` | All deliveries: status (MENUNGGU, DIKIRIM, TIBA), courier, customer, date |
| `/delivery/[id]` | Delivery detail: items, address, courier, status timeline |
| `/delivery/assign` | Assign courier to pending deliveries |

**API Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/deliveries` | All deliveries, filterable by status |
| `POST /admin/deliveries/{id}/assign` | Assign courier to delivery |
| `PATCH /admin/deliveries/{id}/status` | Update: DIKIRIM → TIBA |
| `GET /mobile/deliveries` | Courier: my assigned deliveries (mobile app) |

**Migration:**

```sql
-- Add delivery tracking to transaksi_penjualan metadata
-- Use existing columns: status_transaksi tracks payment,
-- add delivery fields via JSONB extension or new table:
CREATE TABLE IF NOT EXISTS koptumbuh.pengiriman (
    pengiriman_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaksi_sample_id TEXT NOT NULL REFERENCES koptumbuh.transaksi_penjualan(transaksi_sample_id),
    koperasi_ref        TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    tipe_pengiriman     TEXT NOT NULL CHECK (tipe_pengiriman IN ('PICKUP','DELIVERY')),
    alamat_tujuan       TEXT,
    kurir_id            TEXT REFERENCES koptumbuh.karyawan_koperasi(karyawan_ref),
    status              TEXT NOT NULL DEFAULT 'MENUNGGU'
                        CHECK (status IN ('MENUNGGU','DIKIRIM','TIBA','GAGAL')),
    dibuat_pada         TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada     TIMESTAMPTZ DEFAULT NOW()
);
```

#### Courier Auto-Tracking

The courier's mobile app sends GPS coordinates every 30 seconds during delivery. The dashboard shows live location. The customer gets WhatsApp updates.

**Tracking table:**

```sql
CREATE TABLE IF NOT EXISTS koptumbuh.pelacakan_kurir (
    pelacakan_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pengiriman_id   UUID NOT NULL REFERENCES koptumbuh.pengiriman(pengiriman_id),
    kurir_id        TEXT NOT NULL REFERENCES koptumbuh.karyawan_koperasi(karyawan_ref),
    latitude        NUMERIC(10,7) NOT NULL,
    longitude       NUMERIC(10,7) NOT NULL,
    akurasi_meter   NUMERIC(8,2),
    kecepatan_kmh   NUMERIC(5,1),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pelacakan_pengiriman ON koptumbuh.pelacakan_kurir(pengiriman_id, created_at DESC);
```

**Mobile app auto-tracking:**

```
Courier opens KopTumbuh app → taps "Mulai Pengiriman" on assigned delivery
  → App starts GPS tracking (30s interval)
  → POST /mobile/deliveries/{id}/track { lat, lng, accuracy, speed }
  → Backend stores in pelacakan_kurir table
  → Backend broadcasts location to dashboard via polling
```

**Mobile API:**

| Endpoint | Purpose |
|----------|---------|
| `POST /mobile/deliveries/{id}/track` | Submit GPS coordinate |
| `GET /mobile/deliveries/{id}/route` | Full route history for this delivery |
| `POST /mobile/deliveries/{id}/start` | Courier: "Mulai Pengiriman" → status DIKIRIM, GPS tracking starts |
| `POST /mobile/deliveries/{id}/arrive` | Courier: "Tandai Telah Tiba" → status TIBA, GPS tracking stops |

**Admin dashboard — live tracking page (`/delivery/track`):**

```
┌────────────────────────────────────────────────────────────┐
│  🛵 Live Tracking — Pengiriman #DEL-001                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              🗺️  Google Maps / Leaflet                 │  │
│  │                                                       │  │
│  │    🏪 Koperasi ──── 🛵 Kurir ──── 📍 Pelanggan       │  │
│  │    (start)          (live)         (destination)      │  │
│  │                                                       │  │
│  │    Route: ● ● ● ● ●                                    │  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  Kurir: Budi Santoso     Status: 🟢 Dalam Perjalanan        │
│  Kecepatan: 25 km/h     Estimasi Tiba: 15 menit             │
│  Tujuan: Jl. Raya Jonggol No. 42                           │
│                                                             │
│  Timeline:                                                  │
│  10:15  📦 Barang diambil dari gudang                       │
│  10:20  🛵 Kurir berangkat                                  │
│  10:25  📍 Di Jl. Raya Cibinong (2.3 km dari tujuan)       │
│  10:30  📍 Di Jl. Jonggol (0.5 km dari tujuan)              │
└────────────────────────────────────────────────────────────┘
```

**Customer WhatsApp notification:**

When courier starts: "🛵 Pesanan Anda sedang diantar oleh Budi. Estimasi tiba: 15 menit."

When courier is near: "📍 Kurir sudah di dekat lokasi Anda (500m). Siapkan pembayaran."

When arrived: "✅ Pesanan Anda telah tiba. Selamat berbelanja!"

**Live tracking endpoint:**

| Endpoint | Purpose |
|----------|---------|
| `GET /admin/deliveries/{id}/live` | Current courier position (latest GPS point) |
| `GET /admin/deliveries/{id}/route` | Full route history (all GPS points) |
| `GET /admin/deliveries/active` | All currently active deliveries with courier positions |

**Dashboard page:**

| Route | Content |
|-------|---------|
| `/delivery/track/[id]` | Live map tracking: courier position, route, ETA, timeline |

### Subsidy Management

Government-subsidized products (Minyakita, Gas LPG 3kg) have special pricing. SIMKOPDES POS has a subsidy filter. KopTumbuh tracks subsidy status per product.

**Add to produk_koperasi migration:**

```sql
-- Extend product table (additive — does not modify canonical schema DDL)
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS is_subsidi BOOLEAN DEFAULT FALSE;
ALTER TABLE koptumbuh.produk_koperasi ADD COLUMN IF NOT EXISTS nama_subsidi TEXT;
```

**Dashboard page:** `/products/subsidies` — list subsidized products. POS filter: "[Semua] [Sembako] [Subsidi]"

### Post-MVP Features (SIMKOPDES Parity)

Features from the existing SIMKOPDES app documented for after the hackathon:

| Module | SIMKOPDES Page | Post-MVP Scope |
|--------|---------------|----------------|
| **CoopTrade B2B Marketplace** | trade.simkopdes.go.id | Wholesale cooperative-to-cooperative trade — product catalog, company verification (NIB/NPWP), WhatsApp contact, order management |
| **Klinik Desa** | `/klinik-desa/pasien` | Village clinic patient management — patient registration, visit records, billing |
| **Apotek Desa** | `/apotek-desa/daftar-obat` | Village pharmacy — drug inventory, prescriptions, sales |
| **Program Magang** | `/program-magang` | Internship program — applications, placements, evaluations |
| **Jaga Desa** | `/jaga-desa` | Village security patrol — scheduling, incident reporting |
| **Kerja Sama** | `/kerja-sama` | Technology provider directory — vendor listing, service catalog |

### New Migration Tables (additive, post-canonical)

> **Local dev**: All tables below use `koptumbuh` schema.  
> **Shared hackathon DB**: All tables below use `public` schema with `JasaAI_` prefix.  
> Example: `koptumbuh.pinjaman_anggota` → `public.JasaAI_pinjaman_anggota`

```sql
-- Pinjaman (loans) — matches SIMKOPDES pinjaman functionality
CREATE TABLE IF NOT EXISTS koptumbuh.pinjaman_anggota (
    pinjaman_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref        TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref         TEXT NOT NULL REFERENCES koptumbuh.anggota_koperasi(anggota_ref),
    jumlah_pinjaman     NUMERIC(18,2) NOT NULL CHECK (jumlah_pinjaman > 0),
    tenor_bulan         INTEGER NOT NULL CHECK (tenor_bulan > 0),
    bunga_persen        NUMERIC(5,2) DEFAULT 0,
    angsuran_per_bulan  NUMERIC(18,2),
    total_pengembalian  NUMERIC(18,2),
    status              TEXT NOT NULL DEFAULT 'AKTIF' CHECK (status IN ('AKTIF','LUNAS','MACET')),
    tanggal_mulai       DATE NOT NULL DEFAULT CURRENT_DATE,
    tanggal_jatuh_tempo DATE,
    dibuat_pada         TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Banner management
CREATE TABLE IF NOT EXISTS koptumbuh.banner (
    banner_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    judul           TEXT NOT NULL,
    gambar_url      TEXT,
    link_url        TEXT,
    urutan          INTEGER DEFAULT 0,
    status_aktif    BOOLEAN DEFAULT TRUE,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW()
);

-- Member complaints / helpdesk
CREATE TABLE IF NOT EXISTS koptumbuh.pengaduan (
    pengaduan_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    koperasi_ref    TEXT NOT NULL REFERENCES koptumbuh.referensi_koperasi_wilayah(koperasi_ref),
    anggota_ref     TEXT REFERENCES koptumbuh.anggota_koperasi(anggota_ref),
    pengadu_nama    TEXT NOT NULL,
    pengadu_kontak  TEXT,
    kategori        TEXT CHECK (kategori IN ('LAYANAN','PRODUK','KEUANGAN','TEKNIS','LAINNYA')),
    isi_pengaduan   TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'BARU' CHECK (status IN ('BARU','PROSES','SELESAI','DITOLAK')),
    respon          TEXT,
    dibuat_pada     TIMESTAMPTZ DEFAULT NOW(),
    diperbarui_pada TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Phase 5: Intelligence Engine & Export (Hours 34–42)

### Phase 5 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 5.1 | 2.5 hr | Recommendation engine (STOCKOUT_RISK + SLOW_MOVING + RESTOCK) | Phase 3 complete, seed transactions exist | `rekomendasi` table populated | `SELECT COUNT(*) FROM rekomendasi WHERE koperasi_ref='KOP-JasaAI-A1B2C3D4E5F6'` > 0 |
| 5.2 | 1 hr | Recommendation dedup + expiry | 5.1 | No duplicate recs in 24h | Run engine twice → same rec not duplicated |
| 5.3 | 30 min | Celery Beat schedule verification | 5.1 | Beat fires every 4h | Check Celery Beat logs |
| 5.4 | 1.5 hr | SIMKOPDES export (CSV + XLSX + JSON) | Phase 3 complete | File → MinIO → ekspor_log | Download file → verify format |
| 5.5 | 1 hr | Data Quality normalization (Engine 9) | 5.4 | Payment, units, dates standardized | "tunai" → "Cash" in export |
| 5.6 | 30 min | PII sanitization (NIK masking) | 5.4 | NIK masked in logs/exports | 16-digit NIK → `******` in middle |
| 5.7 | 1 hr | BI + Relationship views deployment | 5.3 | All 8 views queryable | `SELECT * FROM v_segmentasi_anggota` returns rows |
| 5.8 | 1 hr | Polling endpoints finalization | Phase 3.7 | All 4 polling intervals return correct data | Simulate poll → new messages/recs returned |
| 5.9 | 30 min | Export history + download endpoint | 5.4 | `GET /admin/export/history` working | Download previous export |

### 5a. Recommendation Engine with Deduplication

```python
# app/workers/recommendations.py

@celery_app.task
def generate_all_recommendations():
    """Called every 4 hours by Celery Beat."""
    cooperatives = db.query(ReferensiKoperasiWilayah.koperasi_ref).all()
    for (koperasi_ref,) in cooperatives:
        generate_for_cooperative.delay(koperasi_ref)

@celery_app.task
def generate_for_cooperative(koperasi_ref: str):
    # Check for existing active recommendations — don't duplicate
    existing = db.query(
        Rekomendasi.produk_sample_id, Rekomendasi.jenis
    ).filter(
        Rekomendasi.koperasi_ref == koperasi_ref,
        Rekomendasi.status.in_(["NEW", "READ"]),
        Rekomendasi.generated_at >= func.now() - timedelta(hours=24)
    ).all()
    existing_set = {(e.produk_sample_id, e.jenis) for e in existing}

    # STOCKOUT_RISK: stock < avg_daily_sales × (lead_time + 2 safety days)
    avg_sales = compute_avg_daily_sales(koperasi_ref, window_days=14)
    for product_id, ads in avg_sales.items():
        if (product_id, "STOCKOUT_RISK") in existing_set:
            continue  # Skip if already recommended in last 24h

        stock = get_current_stock(koperasi_ref, product_id)
        supplier = get_supplier(koperasi_ref, product_id)
        lead_time = supplier.lead_time_hari if supplier else 3
        threshold = ads * (lead_time + 2)
        days_remaining = stock / ads if ads > 0 else float('inf')

        if days_remaining <= threshold:
            priority = "HIGH" if days_remaining <= 3 else "MEDIUM"
            create_recommendation(
                koperasi_ref=koperasi_ref,
                jenis="STOCKOUT_RISK",
                judul=f"Restock {get_product_name(product_id)} dalam {int(days_remaining)} hari",
                isi_rekomendasi=f"Stok {stock} unit. Rata-rata penjualan {ads:.1f}/hari. Lead time supplier {lead_time} hari. Disarankan pesan {(threshold * ads) - stock:.0f} unit.",
                priority=priority,
                produk_sample_id=product_id,
                pemasok_id=supplier.pemasok_id if supplier else None,
                explanation_payload={
                    "current_stock": stock, "avg_daily_sales": ads,
                    "lead_time_days": lead_time, "days_remaining": int(days_remaining),
                    "threshold": threshold, "generated_by": "celery_beat_v1"
                }
            )

    # SLOW_MOVING: no sales in 14 days, stock > 0
    slow = get_slow_moving_products(koperasi_ref, days=14)
    for product in slow:
        if (product.produk_sample_id, "SLOW_MOVING") in existing_set:
            continue
        create_recommendation(
            koperasi_ref=koperasi_ref,
            jenis="SLOW_MOVING",
            judul=f"{product.nama_produk} tidak terjual 14 hari",
            isi_rekomendasi=f"Tidak ada penjualan sejak {product.last_sale}. Stok: {product.stok}. Pertimbangkan promosi atau bundling.",
            priority="LOW",
            produk_sample_id=product.produk_sample_id,
            explanation_payload={"last_sale": str(product.last_sale), "current_stock": product.stok}
        )
```

### 5b. SIMKOPDES Export

```python
# app/services/export_service.py
import csv, io, json
from openpyxl import Workbook
from app.services.storage_service import minio_client
from app.config import settings

async def generate_export(
    ekspor_id: str, koperasi_ref: str, export_type: str,
    format: str, period_start, period_end
) -> str:
    """Query → map to SIMKOPDES format → write file → upload to MinIO → update log."""

    data = await query_export_data(koperasi_ref, export_type, period_start, period_end)
    mapped = [apply_simkopdes_mapping(row) for row in data]

    filename = f"simkopdes_{koperasi_ref}_{export_type}_{period_start:%Y%m%d}-{period_end:%Y%m%d}.{format.lower()}"
    local_path = f"/tmp/{filename}"

    if format == "CSV":
        with open(local_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=mapped[0].keys())
            writer.writeheader()
            writer.writerows(mapped)
    elif format == "XLSX":
        wb = Workbook()
        ws = wb.active
        ws.append(list(mapped[0].keys()))
        for row in mapped:
            ws.append(list(row.values()))
        wb.save(local_path)
    elif format == "JSON":
        with open(local_path, "w") as f:
            json.dump(mapped, f, indent=2, default=str)

    # Upload to MinIO
    object_key = f"{koperasi_ref}/{filename}"
    minio_client.fput_object(settings.MINIO_BUCKET_EXPORTS, object_key, local_path)
    file_url = f"minio://{settings.MINIO_BUCKET_EXPORTS}/{object_key}"
    os.unlink(local_path)

    # Update ekspor_log
    ekspor = db.query(EksporLog).filter(EksporLog.ekspor_id == ekspor_id).first()
    ekspor.status = "SUCCESS"
    ekspor.file_url = file_url
    ekspor.record_count = len(mapped)
    db.commit()

    return file_url
```

### 5c. PII Sanitization

```python
# app/utils/pii.py
import re

NIK_PATTERN = re.compile(r'\b\d{16}\b')

def mask_nik(text: str) -> str:
    """3273011234560001 → 327301******0001"""
    def _mask(m):
        nik = m.group()
        return f"{nik[:6]}******{nik[-4:]}"
    return NIK_PATTERN.sub(_mask, text)

def sanitize_for_log(text: str) -> str:
    """Mask NIK in any text before logging/storing in diagnostics."""
    if not text:
        return text
    return mask_nik(text)
```

### 5d. Real-Time Notification Strategy (Mobile)

The mobile app needs to know when confirmation is ready. Two options:

1. **Polling (MVP)**: Mobile polls `GET /api/v1/mobile/messages?status=NEEDS_CONFIRMATION` every 10 seconds. Simple, no additional infrastructure.
2. **WebSocket (post-MVP)**: FastAPI WebSocket endpoint at `/ws/{user_id}`. Worker pushes events via Redis pub/sub → WebSocket.

**MVP choice: Polling.** The mobile app polls the messages endpoint. A new message with status `PARSED` means confirmation is ready. The AI pipeline completes in 3-8 seconds, so 10-second polling is sufficient.

---

## Phase 6: Testing & Launch (Hours 42–48)

### Phase 6 Sub-Phase Breakdown

| Step | Time | Task | Depends On | Output | Verification |
|------|------|------|------------|--------|-------------|
| 6.1 | 1.5 hr | Integration tests TC-001 through TC-006 | Phase 5 complete, test DB set up | 6 green tests | `pytest backend/tests/ -v` — all pass |
| 6.2 | 1 hr | Edge case testing (insufficient stock, unknown product, corrupted media) | 6.1 | Edge case checklist complete | Each edge case → correct error response |
| 6.3 | 30 min | Database integrity audit (reconciliation, orphans, duplicates) | 6.1 | All audit queries return 0 | 3 SQL queries run clean |
| 6.4 | 1 hr | Environment hardening (CORS, rate limits, pool config, request size caps) | 6.2 | Production-ready config | Attempt abuse → blocked by rate limit / size cap |
| 6.5 | 30 min | Postman/curl test collection | 6.1 | All ~50 endpoints documented with sample payloads | Run collection → all return 200/201 |
| 6.6 | 30 min | Backup verification (pg_dump → MinIO → restore test) | 6.4 | Backup file in MinIO, restore succeeds | Restore to fresh DB → all data present |
| 6.7 | 30 min | Fallback demo video recording | 6.1 | 3-minute walkthrough video file | Play video → covers all 5 demo minutes |
| 6.8 | 30 min | README final review + team section filled | 6.5 | README ready for judges | Another team member reads README → no questions |
| 6.9 | 30 min | Dry-run demo (full script, timed) | 6.7 | Demo flows without errors, under 5 minutes | Timer check: < 300 seconds |

### Phase 6 Deliverables: Postman Collection + Fallback Video

**Postman / curl test collection** (`scripts/api_tests.sh`):

```bash
#!/bin/bash
# KopTumbuh API Test Collection — run against localhost:8000
BASE="http://localhost:8000/api/v1"

echo "=== AUTH ==="
# Login as operator
curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"628123456003","password":"kop123"}' | jq '.success'

echo "=== WEBHOOK ==="
# Send text message
curl -s -X POST $BASE/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"event":"messages.upsert","data":{"key":{"id":"TEST-'$(date +%s)'","remoteJid":"628123456003@s.whatsapp.net"},"message":{"conversation":"Bu Siti beli 2 Beras Premium 5kg","messageType":"conversation"}}}' | jq '.success'

echo "=== MOBILE API ==="
# Dashboard summary (requires token)
TOKEN=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"phone":"628123456003","password":"kop123"}' | jq -r '.data.access_token')
curl -s $BASE/mobile/dashboard/summary -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/mobile/products -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s "$BASE/mobile/products/PRD-001/stock" -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s "$BASE/mobile/transactions?page=1" -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s "$BASE/mobile/members/search?q=Siti" -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s "$BASE/mobile/recommendations?status=NEW" -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/mobile/messages -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/mobile/profile -H "Authorization: Bearer $TOKEN" | jq '.success'

echo "=== ANGGOTA API ==="
TOKEN_A=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" -d '{"phone":"628120000001","password":"kop123"}' | jq -r '.data.access_token')
curl -s $BASE/mobile/my-transactions -H "Authorization: Bearer $TOKEN_A" | jq '.success'
curl -s $BASE/mobile/my-savings -H "Authorization: Bearer $TOKEN_A" | jq '.success'
curl -s "$BASE/mobile/knowledge/search?q=cara" -H "Authorization: Bearer $TOKEN_A" | jq '.success'

echo "=== ADMIN API ==="
curl -s $BASE/admin/dashboard/kpi -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/sales -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/top-products -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/stock-reconciliation -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/member-activity -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/margin -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/slow-moving -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/active-members -H "Authorization: Bearer $TOKEN" | jq '.success'
curl -s $BASE/admin/dashboard/segmentation -H "Authorization: Bearer $TOKEN" | jq '.success'

echo "=== ALL TESTS COMPLETE ==="
```

**Fallback demo video script** (record the night before):

| Timestamp | What to show | Duration |
|-----------|-------------|----------|
| 0:00 | Web dashboard — KPI cards, sales chart | 30s |
| 0:30 | Send WhatsApp message → show webhook log | 45s |
| 1:15 | Show confirmation message on WhatsApp | 30s |
| 1:45 | Reply YA → show database: transaction created, stock updated | 45s |
| 2:30 | Show recommendation engine output (STOCKOUT_RISK alert) | 30s |
| 3:00 | Trigger SIMKOPDES export → download file, show contents | 30s |
| 3:30 | Show reconciliation view: all MATCH | 15s |
| 3:45 | Closing statement | 15s |

Record with OBS or QuickTime. Upload to Google Drive. Link in README as fallback.

### 6a. Test Fixtures

```python
# tests/conftest.py
import pytest, pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_test_db

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def seed_db():
    """Load seed data into test database."""
    # Run seed_demo.sql against test DB
    pass

@pytest.fixture
def auth_headers(seed_db):
    """Get JWT token for test operator user."""
    return {"Authorization": "Bearer test_token_operator"}

@pytest.fixture
def mock_gemini(mocker):
    """Mock Gemini API to avoid real API calls during tests."""
    return mocker.patch("app.services.ai_service.client.models.generate_content")
```

### 6b. Six Verification Tests

| Test | What It Proves |
|------|---------------|
| **TC-001** | Duplicate `wa_message_id` → second call returns `{"status": "duplicate"}`, only 1 row in pesan_masuk |
| **TC-002** | Text "Bu Sari beli 2 Beras Premium 5kg" → pesan_masuk created + parsing_pesan with status DRAFT |
| **TC-003** | Full E2E: webhook → parsing → validation → YA reply → transaksi_penjualan + barang_keluar + inventaris updated |
| **TC-004** | UBAH reply → parsing SUPERSEDED, Redis session cleared, NO transaction created |
| **TC-005** | Manual penyesuaian_stok entry → `v_rekonsiliasi_stok` shows RECONCILED |
| **TC-006** | Trigger export → ekspor_log SUCCESS, file exists in MinIO |

### 6c. Database Integrity Audit

```sql
-- Verify reconciliation
SELECT COUNT(*) AS mismatches
FROM koptumbuh.v_rekonsiliasi_stok
WHERE status_rekonsiliasi NOT IN ('MATCH', 'SNAPSHOT_MISSING');

-- Verify no orphan line items
SELECT COUNT(*) FROM koptumbuh.barang_keluar_produk bk
LEFT JOIN koptumbuh.transaksi_penjualan t ON bk.transaksi_sample_id = t.transaksi_sample_id
WHERE t.transaksi_sample_id IS NULL;

-- Verify idempotency integrity
SELECT whatsapp_message_id, COUNT(*) FROM koptumbuh.pesan_masuk
GROUP BY whatsapp_message_id HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Verify all FK references resolve
SELECT 'pengguna → pengurus' AS check_name, COUNT(*) FROM koptumbuh.pengguna_koptumbuh pu
LEFT JOIN koptumbuh.pengurus_koperasi pk ON pu.pengurus_ref = pk.pengurus_ref
WHERE pu.pengurus_ref IS NOT NULL AND pk.pengurus_ref IS NULL;
-- Expected: 0
```

### 6d. README.md — Hackathon Submission Document

The README is the first thing judges read. It must be thorough, self-contained, and answer every question without requiring them to dig into code. Below is the exact structure and content to include.

---

# KopTumbuh

## Product Name

**KopTumbuh** — *Koperasi Tumbuh* (Growing Cooperatives).

A WhatsApp-first, AI-powered operational platform that upgrades Indonesia's SIMKOPDES cooperative management system with conversational transaction recording and supply chain intelligence.

---

## Problem

Indonesia has over 127,000 active cooperatives (koperasi). The government mandates all of them to report operational data through **SIMKOPDES**, a desktop-based system that requires manual data entry by trained operators.

**The gap:**
- 60%+ of rural cooperatives record daily transactions on **paper notebooks** first, then transcribe them into SIMKOPDES days or weeks later
- Transcription errors, lost notebooks, and delayed reporting are the norm
- Cooperative operators spend 2-4 hours daily on administrative data entry instead of serving customers
- Supply chain decisions (when to restock, what's not selling) are made on intuition, not data
- The SIMKOPDES mobile app has no conversational interface and requires clicking through multiple forms

**KopTumbuh solves this by letting operators record transactions the way they already communicate — by sending a WhatsApp message.**

---

## Target User

| Persona | Role | Pain Point |
|---------|------|------------|
| **Budi Santoso** | Operator Kasir | Spends 3 hours/day transcribing paper notebooks into SIMKOPDES. Uses the mobile app for quick tasks AND the web dashboard for analytics & reporting. |
| **Pak Haji Ahmad** | Anggota (Cooperative Member) | Has no visibility into his savings balance or purchase history. Has to visit the koperasi counter and ask the operator to look it up. Wants self-service access. |
| **Agus Wijaya** | Ketua Koperasi | No real-time visibility into daily sales. Only sees reports at monthly meetings. Uses the mobile app to monitor KPIs on-the-go. |
| **Ratna Dewi** | Bendahara / Admin | Reconciles financial reports manually. Spends a full day before each RAT compiling data. Uses mobile for quick checks, web for deep financial work. |

---

## Selected Theme

**Accelerating Digital Transformation for Rural Economic Institutions.**

KopTumbuh addresses the gap between government digitalization mandates (SIMKOPDES) and the on-the-ground reality of rural cooperatives. It doesn't replace SIMKOPDES — it makes compliance effortless by capturing data at the source (WhatsApp) and exporting to the required format.

---

## Solution Overview

KopTumbuh is a **three-component system**:

```
Mobile App (Operator)          Web Dashboard (Admin/Pembina)
        │                              │
        ▼                              ▼
  ┌─────────────────────────────────────────┐
  │           Backend API (FastAPI)          │
  │  ┌─────────────────────────────────┐    │
  │  │  WhatsApp Pipeline (Evolution)  │    │
  │  │  AI Extraction (Gemini)          │    │
  │  │  Validation Engine (No AI Math) │    │
  │  │  PostgreSQL + Redis + MinIO     │    │
  │  └─────────────────────────────────┘    │
  └─────────────────────────────────────────┘
```

**How it works in 30 seconds:**
1. Operator sends WhatsApp: *"Bu Siti beli 2 Beras 5kg, 1 Minyak Goreng 2L, bayar tunai"*
2. AI extracts entities (products, quantities, customer, payment method)
3. System looks up actual database prices — **never trusts AI math**
4. Operator receives a confirmation message: *YA / UBAH / BATAL*
5. Operator replies `YA` → transaction committed to ledger, inventory updated
6. Dashboard shows real-time sales, stock alerts, and AI recommendations

---

## Features

### Core Transaction Flow
- **WhatsApp conversational recording** — text, voice notes, and receipt photos
- **AI entity extraction** — Gemini 2.5 Flash (multimodal: text, voice, images) for Indonesian language
- **Human-in-the-loop confirmation** — YA/UBAH/BATAL before any data is committed
- **Deterministic math engine** — AI extracts entities only; all totals calculated from database prices
- **Atomic ledger updates** — single PostgreSQL transaction per confirmed sale

### Supply Chain Intelligence
- **Stockout risk alerts** — predictive restock recommendations based on sales velocity and supplier lead times
- **Slow-moving product detection** — flags items with zero sales in 14 days
- **Supplier management** — lead time tracking, purchase history

### Government Compliance
- **SIMKOPDES-compatible data model** — all 27 core tables match government schema
- **One-click export** — CSV, XLSX, and JSON formats with field mapping
- **RAT report readiness** — Annual Member Meeting financial reports always up to date

### Multi-Tenant Architecture
- **Role-based access** — OPERATOR, KETUA, BENDAHARA, PEMBINA, ADMIN
- **Cooperative isolation** — all data scoped through `referensi_koperasi_wilayah` HUB pattern
- **Hierarchical regions** — Provinsi → Kabupaten/Kota → Kecamatan → Desa/Kelurahan

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend API** | Python 3.11+ / FastAPI | Async REST API, auto OpenAPI docs |
| **Async Workers** | Celery + Redis | Message pipeline, AI processing, periodic tasks |
| **Database** | PostgreSQL 15 + pgcrypto | Government-compatible schema, 40 tables, 5 analytical views |
| **Cache / Queue** | Redis 7 | Celery broker, session state, rate limiting |
| **Object Storage** | MinIO (S3-compatible) | Audio, images, exports |
| **WhatsApp Transport** | Evolution API (Baileys) | Self-hosted, no token expiry, QR-code pairing |
| **AI / NLP** | Google Gemini 2.5 Flash | Text parsing, voice transcription, receipt OCR — single multimodal model |
| **Web Dashboard** | Next.js 14 + Tailwind CSS + shadcn/ui | Admin analytics, supply chain, export |
| **Mobile App** | Flutter (built separately) | Operator-facing transaction interface |
| **Infrastructure** | Docker Compose | 4 services: PostgreSQL, Redis, MinIO, Evolution API |
| **Auth** | JWT (python-jose) + bcrypt | Stateless, mobile + web compatible |

---

## Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        WHATSAPP USER                             │
│              (Cooperative Operator — any phone)                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │ Text / Voice / Photo
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                   EVOLUTION API (Docker)                          │
│         WhatsApp Web Protocol — QR-paired, no tokens              │
└────────┬──────────────────────────────────┬──────────────────────┘
         │ Inbound Webhook (POST)           │ Outbound (send)
         ▼                                  ▼
┌─────────────────────┐           ┌─────────────────────┐
│   FastAPI Webhook   │           │  Outbound Dispatcher │
│  • Rate limit       │           │  • Format message    │
│  • Idempotency      │           │  • Send via Evolution│
│  • Validate bounds  │           │  • Log to notifikasi │
│  • INSERT pesan_    │           └─────────────────────┘
│    masuk             │                     ▲
│  • Return 200 OK     │                     │
└─────────┬───────────┘                     │
          │ Push to Queue                    │
          ▼                                  │
┌─────────────────────┐           ┌─────────────────────┐
│    Celery Workers    │           │  Confirmation State │
│  ┌─────────────────┐ │           │      Machine        │
│  │ Audio → Gemini  │ │           │  YA / UBAH / BATAL  │
│  │ Image → Vision  │ │           └─────────────────────┘
│  │ Text  → Parser  │ │                     ▲
│  └────────┬────────┘ │                     │
│           │           │           ┌─────────────────────┐
│           ▼           │           │  Atomic DB Commit   │
│  ┌─────────────────┐ │           │  • transaksi_        │
│  │ Validation      │ │           │    penjualan         │
│  │ • Entity match  │ │           │  • barang_keluar     │
│  │ • DB price      │ │           │  • inventaris update │
│  │ • Math engine   │ │           │  • konfirmasi        │
│  └────────┬────────┘ │           └─────────────────────┘
└───────────┼──────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│              PostgreSQL 15 (koptumbuh schema)                     │
│  40 tables • 5 analytical views • 9 auto-update triggers          │
│  GIN full-text search • pgcrypto UUID generation                  │
└──────────────────────────────────────────────────────────────────┘
            │                              ▲
            ▼                              │
┌─────────────────────┐           ┌─────────────────────┐
│  Web Dashboard       │           │  Mobile App         │
│  (Next.js 14)        │           │  (Flutter)          │
│  • Admin analytics   │           │  • Operator view    │
│  • Supply chain      │           │  • Transactions     │
│  • Member mgmt       │           │  • Inventory        │
│  • SIMKOPDES export  │           │  • Recommendations  │
└─────────────────────┘           └─────────────────────┘
```

### Database Architecture (HUB Pattern)

All 40 tables connect through a single **central hub**:

```
referensi_wilayah
       │
       ▼
referensi_koperasi_wilayah  ← CENTRAL HUB (every table FKs here)
       │
       ├── profil_koperasi (1:0..1)
       ├── pengurus_koperasi
       ├── karyawan_koperasi
       ├── anggota_koperasi ── simpanan_anggota
       ├── produk_koperasi ── inventaris_produk, barang_masuk, barang_keluar
       ├── transaksi_penjualan ── barang_keluar_produk, relasi_transaksi_pihak
       ├── gerai_koperasi, aset_koperasi, dokumen_koperasi
       ├── modal_koperasi, akun_bank_koperasi
       ├── pengajuan_* (4 tables)
       ├── rat_koperasi
       └── [14 KopTumbuh extension tables]
```

This pattern ensures:
- **Region-based multi-tenancy** — query all cooperatives in one kecamatan with a single join
- **Historical integrity** — if a cooperative changes legal entity, transaction history is preserved
- **SIMKOPDES export compatibility** — exact field mapping to government format

---

## How to Run

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for web dashboard)
- Google Gemini API key
- A WhatsApp number (any personal number works)

### Quick Start (5 minutes)

```bash
# 1. Clone and configure
git clone https://github.com/your-team/koptumbuh
cd koptumbuh
cp backend/.env.example backend/.env
# Edit .env — add your GEMINI_API_KEY

# 2. Start all services
docker compose -f backend/docker-compose.yml up -d
# Wait for healthy: postgres, redis, minio, evolution

# 3. Pair WhatsApp
# Open http://localhost:8080 → create instance "koptumbuh" → scan QR code with WhatsApp
# Configure webhook: http://api:8000/api/v1/webhooks/whatsapp

# 4. Seed demo data
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -f /docker-entrypoint-initdb.d/02_seed.sql

# 5. Start backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 6. Start Celery worker (separate terminal)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# 7. Start Celery Beat (separate terminal — for recommendations)
celery -A app.workers.celery_app beat --loglevel=info

# 8. Start web dashboard (separate terminal)
cd web-dashboard
npm install
npm run dev
# Open http://localhost:3000

# 9. Verify
curl http://localhost:8000/health  # {"status": "ok", "db": "connected", "redis": "connected", "minio": "connected", "evolution": "connected"}
```

### Development without WhatsApp

Send test messages directly to the webhook:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -H "X-Dev-Mode: true" \
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

---

## Demo Account

| Role | Phone / Username | Password | Access |
|------|-----------------|----------|--------|
| Operator (Budi) | `628123456003` | `kop123` | Mobile app, transaction recording |
| Ketua (Agus) | `628123456001` | `kop123` | Web dashboard, all reports |
| Bendahara (Ratna) | `628123456002` | `kop123` | Financial views, export |
| Pembina | `pembina@koptumbuh.id` | `kop123` | Multi-cooperative oversight |

**Demo Cooperative**: Koperasi Tumbuh Bersama, Desa Nanggewer, Kecamatan Cibinong, Kabupaten Bogor, Jawa Barat.

**Pre-loaded data**: 5 products with inventory, 5 members with savings, 5 historical transactions across the last 7 days, 1 supplier, legal documents, RAT record.

---

## Data Model

The database uses a **government-compatible schema** (`koptumbuh`) with 40 tables organized in 7 groups:

| Group | Tables | Description |
|-------|--------|-------------|
| **Master & Reference** | 4 | Administrative regions, document types, outlet types, commodity categories |
| **Identity & Organization** | 7 | Cooperative profile, board, employees, legal documents, KBLI codes, assets, outlets |
| **Members & Participation** | 2 | Members, savings/deposits |
| **Business Operations** | 5 | Products, sales transactions, inbound/outbound goods, inventory |
| **Finance & Applications** | 6 | Bank accounts, capital, financing applications, partnership applications, domain applications |
| **Village & Governance** | 3 | Village commodities, village demographics, Annual Member Meetings (RAT) |
| **KopTumbuh Extensions** | 13 | Users, suppliers, customers, WhatsApp messages, AI parsing, confirmations, transaction-party relations, knowledge articles, recommendations, notifications, stock adjustments, integration mappings, export logs |

**5 Analytical Views**: `v_stok_terhitung` (movement-based stock), `v_rekonsiliasi_stok` (inventory reconciliation), `v_penjualan_harian` (daily sales), `v_produk_terlaris` (top products), `v_aktivitas_anggota` (member activity).

Full DDL is in `database/koptumbuh_updated_minimal_data_model.sql`. An ERD diagram is available in the `docs/` folder.

---

## AI Use Disclosure

KopTumbuh uses **Google Gemini** in the following ways:

| AI Model | Input | Output | Safeguard |
|----------|-------|--------|-----------|
| **Gemini 2.5 Flash** (structured output) | Free-text transaction description (Indonesian) | Structured JSON with product names, quantities, customer, payment method | `temperature=0.0`, response schema enforced, entity resolution against database |
| **Gemini 2.5 Flash** (audio) | Voice notes (≤ 60 seconds, Indonesian) | Transcribed text | Duration enforced by ffprobe, transcription re-validated by text parser |
| **Gemini 2.5 Flash** (multimodal) | Receipt/product photos | Structured JSON with visible line items | Confidence threshold < 0.7 flags for human review; 10MB file cap |

A single model handles all three input types — text, audio, and images.

**Critical guardrail — The "No AI Math" Rule:**

The AI is used **only for entity extraction** (product name, quantity, customer). It is **never** trusted to calculate totals, prices, or financial values. All monetary calculations use database prices via deterministic server-side arithmetic:

```python
# NOT this (trusting AI):
total = ai_response.total  # ❌ AI hallucination risk

# THIS (database as source of truth):
db_price = float(product.harga_jual)        # ← PostgreSQL lookup
subtotal = item["quantity"] * db_price      # ← Server-side math
```

If the AI extracts a product name that doesn't match the database catalog, the transaction is flagged for human review and **no data is committed**.

**Data sent to Gemini**: Only the text of the operator's WhatsApp message, the audio of voice notes, or the image of receipts. No member PII, no NIK numbers (masked before any processing), and no historical transaction data are included in AI prompts.

---

## Security & Privacy Notes

### Data Protection
- **NIK masking**: 16-digit Indonesian ID numbers are automatically masked (`327301******0001`) in logs and diagnostic output before storage
- **No PII in AI prompts**: Member data, NIK, and financial history are never sent to Gemini
- **Database-level isolation**: Multi-tenant data separation through `koperasi_ref` foreign key on every table
- **JWT authentication**: Stateless tokens with role-based claims, refresh token rotation

### Input Validation
- **4000 character limit** on text messages (prevents prompt injection abuse)
- **60 second audio cap** (enforced at worker level via ffprobe)
- **10MB file size cap** at API gateway
- **Rate limiting**: 60 requests/minute per WhatsApp number (Redis token bucket)

### Idempotency
- **Two-layer deduplication**: Redis SETNX lock (fast) + PostgreSQL UNIQUE constraint (authoritative)
- WhatsApp message IDs are never processed twice, even with webhook retry storms

### Transaction Integrity
- **Atomic commits**: Confirmed transactions use PostgreSQL `BEGIN/COMMIT` blocks — partial writes impossible
- **Inventory reconciliation**: `v_rekonsiliasi_stok` view detects any discrepancy between calculated and recorded stock

---

## Pilot Plan

### Phase 1: Single-Cooperative Trial (Month 1)
- **Location**: Koperasi Tumbuh Bersama, Desa Nanggewer, Kecamatan Cibinong, Kabupaten Bogor, Jawa Barat
- **Users**: 3 (Operator, Ketua, Bendahara)
- **Duration**: 2 weeks of parallel run — operators record transactions in both paper and WhatsApp
- **Success criteria**: ≥ 90% transaction capture rate via WhatsApp, zero data loss, < 5% entity resolution failures

### Phase 2: Multi-Cooperative Expansion (Month 2–3)
- **Scale**: 5–10 cooperatives in Kabupaten Bogor
- **Add**: Pembina role for regional cooperative coaches
- **Success criteria**: Monthly RAT reports generated from KopTumbuh data match manual reports within 2% margin

### Phase 3: SIMKOPDES Integration (Month 4–6)
- **Feature**: Direct API integration with SIMKOPDES (not just file export)
- **Scale**: 50+ cooperatives
- **Success criteria**: End-to-end WhatsApp transaction → SIMKOPDES database in < 60 seconds

---

## Team

| Name | Role | Responsibilities |
|------|------|-----------------|
| [Name] | Backend Engineer | FastAPI API, Celery workers, AI pipeline, database |
| [Name] | Frontend Engineer | Next.js web dashboard, API integration, charts |
| [Name] | Mobile Engineer | Flutter mobile app, WhatsApp UX |
| [Name] | Product / Domain Expert | Cooperative operations knowledge, SIMKOPDES compliance, pilot coordination |

**Team Name**: JasaAI  
**Table Prefix**: `JasaAI_` (used on shared hackathon database for all extension tables)  
**Cooperative Reference**: `KOP-JasaAI`

---

*Built for [Hackathon Name], July 2026. KopTumbuh is not affiliated with or endorsed by the Indonesian Ministry of Cooperatives and SMEs.*



### 6e. Demo Script (5-Minute Hackathon Flow)

```
Minute 1 — INTRO
  Open web dashboard → show KPI cards, sales chart, top products.
  "Koperasi Tumbuh Bersama, Desa Nanggewer, Bogor. 5 produk, 5 anggota, omzet 7 hari terakhir."

Minute 2 — WHATSAPP TRANSACTION
  Show terminal: POST /webhooks/whatsapp with "Bu Siti beli 2 Beras Premium 5kg dan 1 Minyak Goreng 2L, bayar tunai"
  → Returns {"status": "queued"} in < 500ms
  → Show Celery logs: process_message → extract → parse → validate
  → Show confirmation message delivered to WhatsApp simulator

Minute 3 — AI PARSING RESULT
  Show the confirmation message with:
    • Beras Premium 5kg  2 × Rp 65.000 = Rp 130.000
    • Minyak Goreng 2L    1 × Rp 28.000 = Rp  28.000
    Total: Rp 158.000
  "Gemini 2.5 Flash extracted the entities. Prices came from DATABASE, not AI. Total calculated with deterministic math."
  
  → Reply "YA"
  → Show database: SELECT * FROM transaksi_penjualan WHERE transaksi_sample_id = 'TRX-...'
  → Show inventory updated: SELECT stok FROM inventaris_produk WHERE produk_sample_id = 'PRD-001'

Minute 4 — INTELLIGENCE
  Open web dashboard → Recommendations tab
  Show STOCKOUT_RISK alert: "Telur Ayam 1kg tersisa 12 unit — pesan sekarang"
  Show SLOW_MOVING alert if applicable
  "AI-generated recommendations every 4 hours. Supply chain intelligence for rural cooperatives."

Minute 5 — EXPORT & CLOSE
  Trigger SIMKOPDES export → download CSV
  Show the reconciliation view: all MATCH — no discrepancies
  "KopTumbuh: WhatsApp-first, AI-powered, SIMKOPDES-compatible. Upgrade for Indonesia's cooperatives."
```

---

## Data Flow: Complete Happy Path

```
Operator: "Bu Siti beli 2 Beras Premium 5kg, 1 Minyak Goreng 2L, bayar tunai"
    │
    ▼
WhatsApp Gateway
    │ POST /api/v1/webhooks/whatsapp
    ▼
┌────────────────────────┐
│ FastAPI Webhook        │
│ • Rate limit check     │
│ • Resolve user (phone) │
│ • Validate bounds      │
│ • Redis idempotency    │
│ • INSERT pesan_masuk   │  → Status: RECEIVED
│ • Push to Celery       │
│ • Return 200 (<500ms)  │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Celery Chain           │
│ process_message()      │
│  → parse_text()        │  Gemini 2.5 Flash
│  → validate_parsing()  │  Entity resolution + DB math
│  → dispatch_confirm()  │  WhatsApp message + Redis session
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Validation Worker      │
│ "Beras Premium 5kg"    │  → ILIKE match → PRD-001
│ "Minyak Goreng 2L"     │  → ILIKE match → PRD-002
│ "Bu Siti"              │  → ILIKE match → ANG-002
│                        │
│ DB price: 65000, 28000 │  ← FROM DATABASE, not AI
│ Math: 2×65000=130000   │  ← DATABASE MATH
│        1×28000= 28000  │
│ Total: 158000          │
│                        │
│ Status: VALID          │
│ Redis: AWAITING_       │
│   CONFIRMATION (15min) │
└───────────┬────────────┘
            │
            ▼
    📋 Konfirmasi Transaksi
    • Beras Premium 5kg  2×65.000 = 130.000
    • Minyak Goreng 2L    1×28.000 =  28.000
    Total: Rp 158.000
    YA / UBAH / BATAL
            │
            │ User replies "YA"
            ▼
┌────────────────────────┐
│ Confirmation Handler   │
│ Check Redis → active   │
│ Match "YA" → commit    │
│                        │
│ DB TRANSACTION (atomic)│
│  INSERT transaksi      │
│  INSERT barang_keluar  │
│  UPDATE inventaris     │
│  INSERT konfirmasi     │
│  INSERT relasi         │
│  DELETE Redis session  │
└───────────┬────────────┘
            │
            ▼
    ✅ Transaksi berhasil disimpan!
    ID: TRX-20260710-ABC123
    Total: Rp 158.000
```

---

## Phase Timeline

| Phase | Hours | Focus | Key Deliverable |
|-------|-------|-------|-----------------|
| **1** | 0–6 | Infra & DB | Docker up, schema migrated, seed loaded (1 cooperative, 5 products, 5 members, 5 historical transactions), health checks green |
| **2** | 6–16 | WhatsApp Pipeline | End-to-end: webhook → AI extract → entity resolve → validation → confirmation dispatched |
| **3** | 16–24 | Confirmation & Commit | YA/UBAH/BATAL state machine, atomic DB transactions, inventory updates |
| **4** | 24–34 | Web Dashboard | ~30 pages: analytics, inventory (5 pages), supply chain (4 pages), cooperatives, members, finance, village, export, settings |
| **5** | 34–42 | Intelligence & Export | Recommendation engine (with dedup), SIMKOPDES export, PII sanitization, real-time polling |
| **6** | 42–48 | Testing & Launch | 6 integration tests, edge cases, integrity audit clean, demo script ready, fallback video recorded |

### Performance Targets

Every developer should know when their work is "done." These are the benchmarks:

| Operation | Target | Measured As |
|-----------|--------|-------------|
| Webhook response | < 500ms | POST /webhooks/whatsapp → 200 OK |
| AI extraction (text) | < 3s | Gemini API call + response parse |
| AI extraction (audio) | < 8s | Download + Gemini transcription + parse |
| AI extraction (image) | < 5s | Gemini Vision OCR + parse |
| Confirmation dispatch | < 10s total | Webhook received → WhatsApp confirmation sent |
| Dashboard API | < 200ms | Any GET /admin/dashboard/* endpoint |
| List endpoints | < 300ms | Paginated queries (20 items) |
| Export generation | < 30s | 1000-row CSV/XLSX/JSON |
| Database query (indexed) | < 50ms | Any SELECT using indexed columns |

### Sub-Phase Breakdowns

Each phase below has numbered sub-phases with: **Time budget**, **Dependencies**, **Input**, **Output**, and **Verification command**. Complete sub-phases in order — each builds on the previous.

### Parallel Development Strategy

The three projects can be built simultaneously by three people:

```
Hour 0 ──────────────────────────────────────────────── Hour 48
│                                                          │
│  Developer 1: Backend API                                │
│  [Phase 1: Infra] [Phase 2: Pipeline  ] [Phase 3: TX   ]│
│                   [Phase 5: Intelligence               ] │
│  [Phase 6: Testing                                    ] │
│                                                          │
│  Developer 2: Web Dashboard                              │
│  [Wait for API ] [Phase 4: All 24 pages                ] │
│  [contracts    ] [Build against running API             ] │
│                                                          │
│  Developer 3: Mobile App (Flutter)                       │
│  [Build against API contracts from Hour 0              ] │
│  [Mock API responses → swap to real API at Hour 30     ] │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Mobile developer (Dev 3) can start immediately at Hour 0** — the API contracts in this document are the spec. Build all screens against mocked JSON responses. Swap to the real backend at Hour 30+ when it stabilizes. This means all three projects can be demo-ready at Hour 48.

---

## Risk Matrix

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Evolution API session disconnects** | Medium | QR re-scan restores session. Evolution stores session data in a Docker volume — survives container restarts. Not a token expiry issue (no tokens). |
| Gemini latency > WhatsApp timeout | **High** | Async architecture — webhook returns 200 before AI runs. Celery retries on failure. |
| Gemini hallucinates product names | Medium | Entity resolution catches mismatches. Unmatched products → NEEDS_REVIEW, no transaction created. |
| PostgreSQL UNIQUE constraint violation on duplicate wa_message_id | Low | Redis lock (fast) + catch IntegrityError + return friendly "duplicate" response. |
| Redis crash loses session state | Medium | State is ephemeral by design. User resends message → treated as new. 15-min TTL auto-cleans. |
| Concurrent YA (double-tap) | Low | Redis session deleted BEFORE commit. Second YA finds no session → routed to parser. |
| Large receipt photo OCR fails | Medium | 10MB cap. If extraction confidence < 0.7 → flag NEEDS_REVIEW, skip auto-confirmation. |
| Recommendation spam (same rec every 4h) | Medium | Dedup: check existing NEW/READ recs in last 24h before creating. `explanation_payload` tracks generation metadata. |
| Celery worker crash mid-chain | Low | Celery `task_acks_late=True`. Failed tasks retry with exponential backoff. Chain resumes from failed step. |
| Gemini API quota exceeded | Low | Catch 429 responses, pause queue, alert admin via notifikasi_log. |

---

## Verification Checklists

### Phase 1
```bash
docker compose up -d
docker compose ps  # All 3 healthy
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='koptumbuh';"  # 40
docker exec koptumbuh-db psql -U dev_admin -d koptumbuh_dev -c \
  "SELECT nama_koperasi FROM koptumbuh.profil_koperasi;"  # "Koperasi Tumbuh Bersama"
python backend/scripts/verify_infra.py  # All green
```

### Phase 2
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"message_id":"TEST-001","sender_phone":"628123456003","message_type":"text","text_content":"Bu Siti beli 2 Beras Premium 5kg"}'
# → {"success": true, "data": {"status": "queued", "pesan_id": "..."}}
# Check Celery logs for chain execution
# Query: SELECT status, extracted_payload FROM koptumbuh.parsing_pesan WHERE pesan_id = '...'
```

### Phase 3
- Send webhook → confirm YA → verify: `SELECT * FROM koptumbuh.transaksi_penjualan ORDER BY dibuat_pada DESC LIMIT 1`
- Send webhook → confirm UBAH → verify: NO new transaction, Redis key deleted
- `SELECT * FROM koptumbuh.v_stok_terhitung` → verify stock math is correct

### Phase 4
- Login at `http://localhost:3000`
- Navigate all 24 pages — verify data loaded from backend
- Verify responsive layout (desktop + tablet)

### Phase 5
- `SELECT COUNT(*) FROM koptumbuh.rekomendasi WHERE koperasi_ref = 'KOP-001'` → has entries
- Trigger export via dashboard → verify file download
- Send webhook with 16-digit NIK in text → verify masked in pesan_masuk.raw_text

### Phase 6
```bash
pytest backend/tests/ -v  # All 6 pass
# Run integrity audit queries → all return 0
# Run demo script → all 5 minutes flow without errors
```

---

---

## Architecture Decision Records

Formal documentation of the key architectural choices made during design.

### ADR-001 — WhatsApp as primary input channel

**Decision:** Use WhatsApp (via Evolution API) for transaction recording.  
**Reason:** Cooperative operators already use WhatsApp daily. Zero learning curve. No new app to install for core recording flow.  
**Trade-off:** Provider dependency on WhatsApp Web protocol. Mitigated by manual entry fallback in the mobile app. Evolution API avoids Meta Cloud API token expiry.

### ADR-002 — Human confirmation before any data write

**Decision:** Require explicit YA/UBAH/BATAL before committing AI-extracted data.  
**Reason:** AI makes mistakes. Cooperative financial records require trust. Human-in-the-loop ensures data integrity.  
**Trade-off:** Adds one interaction round-trip (3-8 seconds). Acceptable — the operator is already at the counter.

### ADR-003 — Separate operational DB, SIMKOPDES via export

**Decision:** Use KopTumbuh PostgreSQL as the operational database. Export to SIMKOPDES format. No direct API write to government systems.  
**Reason:** No production SIMKOPDES API access is assumed during hackathon. Export + mapping is the only safe integration path.  
**Trade-off:** Requires periodic export and potential sync lag. Mitigated by `mapping_integrasi` table tracking export status.

### ADR-004 — Rules-first supply chain, ML augmentation later

**Decision:** Use deterministic formulas (ADS, days_remaining, lead_time calculations) for stockout prediction and recommendations.  
**Reason:** Explainable, auditable, fast to implement. No ML training data required.  
**Trade-off:** Less adaptive than ML models for complex patterns. Enables future ML layer on top of existing engine output.

### ADR-005 — Movement-based stock as truth source

**Decision:** Calculate stock from SUM(barang_masuk) - SUM(barang_keluar) + SUM(penyesuaian). Compare against inventaris_produk snapshot for reconciliation.  
**Reason:** Auditable. Every stock change traces back to a confirmed transaction or adjustment. The snapshot can drift — the movement log cannot.  
**Trade-off:** Requires a trusted opening balance. The `v_rekonsiliasi_stok` view catches any discrepancy.

### ADR-006 — Gemini 2.5 Flash as unified AI model

**Decision:** Use a single multimodal model (Gemini 2.5 Flash) for text extraction, audio transcription, and image OCR.  
**Reason:** One API key, one SDK, one model for all three modes. Simpler than OpenAI (Whisper + GPT-4o-mini + GPT-4o-mini Vision = three models).  
**Trade-off:** Google dependency. Mitigated by `ai_service.py` abstraction — swap providers by changing one file.

### ADR-007 — Evolution API over Meta Cloud API

**Decision:** Self-host Evolution API (WhatsApp Web protocol) instead of Meta Cloud API.  
**Reason:** No 24-hour token expiry. No Meta Business verification. QR-code pairing works with any personal number.  
**Trade-off:** Unofficial protocol — WhatsApp could block it. Mitigated by `whatsapp_service.py` abstraction — swap to Meta Cloud API by changing one file.

### ADR-008 — UUIDs for extension tables, TEXT for core tables

**Decision:** KopTumbuh extension tables use UUID primary keys. Core SIMKOPDES tables keep TEXT primary keys.  
**Reason:** Core tables must match government identifiers for export compatibility. Extension tables benefit from UUID collision resistance and no sequence bottlenecks.  
**Trade-off:** Mixed PK types. Extension tables FK to core TEXT keys — acceptable for MVP scale.

---

## Architecture Validation Checklist

Before claiming the hackathon build is complete, verify every layer:

### Layer 1 — Users & Channels
- [ ] Text input via WhatsApp works end-to-end
- [ ] Voice note input has fallback behavior (duration cap, ffprobe check)
- [ ] Photo/receipt input has fallback behavior (confidence < 0.7 → NEEDS_REVIEW)
- [ ] Unauthorized sender (unknown WhatsApp number) → silent reject with log

### Layer 2 — Gateway
- [ ] Evolution API webhook signature validated
- [ ] Duplicate `whatsapp_message_id` → idempotency check passes (Redis + DB)
- [ ] Rate limit enforced (60/min per sender, Redis token bucket)
- [ ] Sender phone resolved to `pengguna_id` + `koperasi_ref`
- [ ] Webhook returns 200 within 500ms

### Layer 3 — Multimodal Processing
- [ ] Text → Gemini extracts intent, customer, line_items, payment
- [ ] Voice → Gemini transcribes to Indonesian text → text parser
- [ ] Photo → Gemini OCR extracts visible line items
- [ ] Confidence score returned with every parse
- [ ] `ambiguous_fields` returned when confidence < 0.7

### Layer 4 — Validation & Confirmation
- [ ] Entity resolution matches product names (exact → ILIKE → word-overlap)
- [ ] AI-computed totals are DISCARDED — DB prices used exclusively
- [ ] YA → atomic transaction commit (transaksi + barang_keluar + inventaris)
- [ ] UBAH → cache cleared, draft superseded, user prompted to re-send
- [ ] BATAL → cache cleared, no data written
- [ ] CONFIRMED is the only state that alters transaction and stock data

### Layer 5 — Core Engines
- [ ] Transaction Engine: all three input modes produce structured drafts
- [ ] Validation Engine: entity resolution + DB math working
- [ ] Supply Chain Engine: stockout risk calculated, lead time factored
- [ ] Recommender Engine: deduplication prevents duplicate recs
- [ ] Export Engine: JSON export produces valid SIMKOPDES-compatible file
- [ ] Reconciliation Engine: v_rekonsiliasi_stok view returns correct status
- [ ] BI Engine: all 6 metrics visible in dashboard
- [ ] Relationship Engine: RFM segmentation returns correct tiers
- [ ] Data Quality Engine: payment/unit normalization active before export

### Layer 6 — Operational Data
- [ ] All 40 tables created in koptumbuh schema
- [ ] Seed data loads without errors
- [ ] HUB pattern enforced (all child tables FK to referensi_koperasi_wilayah)
- [ ] MinIO bucket created, media upload/download works
- [ ] GIN full-text search index on artikel_pengetahuan functional

### Layer 7 — Data Quality
- [ ] Payment method normalization active (cash/Cash/TUNAI → Cash)
- [ ] Unit normalization active (kg/KG/kilogram → KG)
- [ ] Date/time stored as TIMESTAMPTZ, displayed as Asia/Jakarta
- [ ] NIK masked in logs (327301******0001)

### Layer 8 — SIMKOPDES Adapter
- [ ] mapping_integrasi table tracks local → external references
- [ ] Export generates valid CSV, XLSX, and JSON
- [ ] Exported file uploaded to MinIO
- [ ] ekspor_log records export status and file URL
- [ ] No claim of direct SIMKOPDES API access

### Layer 9 — Outputs
- [ ] WhatsApp confirmation template formatted correctly
- [ ] YA/UBAH/BATAL reply handling works
- [ ] Web dashboard loads all ~30 pages without errors
- [ ] Mobile API endpoints return correct data for all 3 roles
- [ ] Mobile app polling refreshes data at correct intervals

### Cross-Cutting
- [ ] JWT auth: login, refresh, role-based access
- [ ] Redis session state: set, read, delete, TTL expiry
- [ ] Celery task retries: exponential backoff on failure
- [ ] Health check endpoint returns all services status
- [ ] Database backup script runs (pg_dump to MinIO)
- [ ] Demo uses synthetic/masked data only
- [ ] No real member NIK exposed in any log or AI prompt
- [ ] `.env.example` documents all required variables

### Deploy & Go-Live Checklist (Demo Day)

Run these in order. Every item must pass before demo.

| # | Check | Command / Verification | Owner |
|---|-------|----------------------|-------|
| 1 | All Docker services healthy | `docker compose ps` — 4 services, all healthy | Backend |
| 2 | Schema + seed loaded | `SELECT count(*) FROM information_schema.tables WHERE table_schema='koptumbuh'` → 48 | Backend |
| 3 | All views return data | `SELECT count(*) FROM v_perbandingan_harga` — no error | Backend |
| 4 | Health endpoint green | `curl localhost:8000/health` → all services OK | Backend |
| 5 | Webhook accepts messages | `curl POST /webhooks/whatsapp` → `{"status":"queued"}` | Backend |
| 6 | AI extraction works | Send test text → check parsing_pesan has extracted_payload | Backend |
| 7 | Celery worker running | Flower dashboard shows worker online | Backend |
| 8 | Celery Beat running | Scheduler log shows next fire times | Backend |
| 9 | Evolution paired | `curl evolution:8080/instance/connectionState/koptumbuh` → `{"state":"open"}` | Backend |
| 10 | Web dashboard loads | Open `localhost:3000` → login page renders | Frontend |
| 11 | Login works | Login with demo credentials → redirected to dashboard | Frontend |
| 12 | All dashboard pages load | Spot-check 5 key pages: /, /analytics, /supply-chain, /pos, /rat | Frontend |
| 13 | Ngrok tunnel active | `curl https://your-ngrok.ngrok-free.app/health` → OK | Backend |
| 14 | Real WhatsApp message works | Send actual WhatsApp to paired number → webhook triggers | All |
| 15 | End-to-end: WA → confirm → DB | Send TX, reply YA → verify in DB | All |
| 16 | Demo script timed | Run full script → under 5 minutes | All |
| 17 | Fallback video ready | 3-minute recording uploaded, link in README | All |
| 18 | README reviewed | Another person reads README → can answer "what is this?" | All |

### Roles & Permissions Matrix

| Role | Mobile App | Web Dashboard | WhatsApp | Core Permissions |
|------|-----------|---------------|----------|-----------------|
| **ANGGOTA** | My Transactions, My Savings, My Loans, Knowledge, Profile | — | ASK_KNOWLEDGE, "SHU saya?" | View own data only |
| **OPERATOR** | All Anggota permissions + Dashboard, Products, Transactions, Restock, Savings, Members, Recommendations, Messages | — | RECORD_SALE, RECORD_RECEIPT, REPORT_PRICE | Record transactions, manage stock, record savings |
| **KETUA** | Dashboard, Products, Transactions, Members, Recommendations (read-only) | — | Same as OPERATOR | View all data, approve large TX |
| **BENDAHARA** | Dashboard, Transactions, Savings, Loans, Finance | — | "SHU koperasi?", "Laporan hari ini?" | Financial data, export, SHU |
| **PEMBINA** | Multi-cooperative dashboard | All dashboard pages (read-only) | — | Cross-cooperative oversight |
| **ADMIN** | All features | All dashboard pages (full CRUD) | — | User management, system config |
| **KURIR** | My Deliveries, Delivery Status | — | "DIKIRIM TRX-xxx", "TIBA TRX-xxx" | View assigned deliveries, update status |
| **ADMIN GUDANG** | — | Inventory, Stock Movements, Warehouse Locations | — | Product CRUD, stock confirmation |
| **ADMIN LOGISTIK** | — | Delivery Management, Courier Assignment | — | Assign courier, track deliveries |

### Webhook Authentication

The WhatsApp webhook endpoint is unauthenticated by design (Evolution API sends events, not authenticated users). Defense layers:

1. **Shared secret**: Evolution API webhook URL includes a secret token: `/webhooks/whatsapp?token=koptumbuh_webhook_secret`
2. **Sender validation**: Only messages from numbers in `pengguna_koptumbuh` are processed. Unknown senders → silent reject with log.
3. **Idempotency**: Duplicate `whatsapp_message_id` → ignored (Redis + DB constraint).
4. **Rate limiting**: Redis token bucket — 60 req/min per sender.
5. **IP allowlist** (optional): Restrict webhook to Evolution API container IP only.

### Data Retention Policy (MVP)

| Data Type | Retention | Reasoning |
|-----------|----------|-----------|
| WhatsApp messages (pesan_masuk) | 90 days | Audit trail for transactions |
| AI parsing results (parsing_pesan) | 90 days | Debug AI accuracy |
| GPS tracking data (pelacakan_kurir) | 7 days | Only active deliveries need live tracking |
| Price comparison data (harga_pasar) | 7 days | Prices expire quickly |
| Export files (MinIO) | 30 days | Regenerate if needed |
| Session state (Redis) | 15 minutes | Ephemeral by design |
| Recommendations | 30 days | Auto-expire via `expires_at` |
| Audit logs (notifikasi_log) | 1 year | Compliance |

---

## Notes

- The canonical schema (`koptumbuh_updated_minimal_data_model.sql`) is **read-only**. Never modified by application code.
- All monetary values use `NUMERIC(18,2)` → Python `Decimal` type.
- All timestamps are `TIMESTAMPTZ` → stored as UTC, displayed as Asia/Jakarta.
- The `referensi_koperasi_wilayah` table is the **CENTRAL HUB** — all child tables FK to it, never directly to `profil_koperasi`.
- Mobile app codebase will be shared later. The API contracts in this document are the integration surface — mobile team builds against these endpoints.
- **API documentation**: FastAPI auto-generates OpenAPI docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc). Screenshot this for hackathon judges.
- **Rollback plan**: All migrations are additive (`CREATE IF NOT EXISTS`, `CREATE OR REPLACE VIEW`). No destructive migrations. Rollback = redeploy previous Docker image. Database backups in MinIO every 6 hours provide point-in-time recovery.
- **Postman collection**: The `scripts/api_tests.sh` script covers all ~50 endpoints. Run `bash scripts/api_tests.sh` to verify the entire API surface in under 60 seconds.
