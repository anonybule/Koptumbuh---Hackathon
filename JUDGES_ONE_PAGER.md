# Judges one-pager — KopTumbuh (JasaAI)

**One line:** WhatsApp chats → confirmed cooperative ledger. AI never invents the money.

## Problem
Village co-ops (180k+) still run on paper/basic POS → stockouts, weak margins, painful SIMKOPDES reporting. Operators already live in WhatsApp.

## Solution
1. Operator sends text / voice / photo on WhatsApp  
2. Gemini extracts **product + qty** only  
3. Prices/totals come from the **database** (**No AI Math**)  
4. Operator replies **YA / UBAH / BATAL** — only YA commits sale + stock  
5. Web + mobile show KPIs, inventory, recs, SIMKOPDES export  

## Why different
| vs typical POS / SaaS | KopTumbuh |
|----------------------|-----------|
| New app + training | WhatsApp-native core path |
| Trust AI totals | DB prices only + human YA gate |
| Parallel data silo | SIMKOPDES-shaped schema + export |

## Demo credentials
```
Login:     628123456003
Password:  kop123
Koperasi:  KOP-JasaAI-A1B2C3D4E5F6
Dashboard: http://localhost:8101  (or npm run dev → :3000)
API docs:  http://localhost:8100/docs
```

## Ports (docker compose)
| Service | URL |
|---------|-----|
| API | http://localhost:8100 |
| Web (root compose) | http://localhost:8101 |
| Evolution | http://localhost:8082 |

## 60-second demo (if WhatsApp down)
**POS Kasir → Demo 1-klik → Dashboard Refresh**

## Ask
Validate the wedge · score the working demo · intros to pilot co-ops / Dinas Koperasi.
