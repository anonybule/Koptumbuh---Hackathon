# Q&A cards — KopTumbuh (JasaAI)

Print or keep open during pitch. Stay honest.

---

### Q: Did you talk to real cooperative operators?
**A:** We grounded the problem in the **SIMKOPDES mandate**, observable WhatsApp-first behavior in Indonesia (90M+ DAU), and the official schema/DDL — not a fabricated field study. Next step is a **3–5 co-op pilot** to validate pricing and workflows.

---

### Q: How is this different from a retail WhatsApp chatbot?
**A:** Three things: (1) **No AI Math** — money always from DB prices; (2) **YA/UBAH/BATAL** human gate before ledger write; (3) **SIMKOPDES-shaped** data + one-click export, not a parallel silo.

---

### Q: Can a village co-op IT person deploy this alone?
**A:** **Not yet without help.** Today: Docker Compose for demo/pilot with a technical partner. Operator day-to-day still needs **no new app** once WhatsApp is paired. Managed hosting is Post-MVP.

---

### Q: What if WhatsApp / Evolution fails on stage?
**A:** **Path B:** Web POS → Demo 1-klik → Dashboard refresh (&lt;60s). Same ledger + stock. We also have `demo_ready.sh` / webhook curl. Prefer reliability over a flaky live QR.

---

### Q: What does Gemini cost?
**A:** Flash is cheap per message (fractions of a rupiah at demo volume). SaaS tiers (Rp 500K–1.5M/mo) are **projections** for pilots — not validated revenue yet. POS path works **without** Gemini.

---

### Q: Why not just use a normal POS?
**A:** POS assumes training, devices, and a new habit. Co-op operators already message on WhatsApp. We keep POS as **fallback**, not the primary wedge.

---

### Q: Is the e-commerce price scrape real?
**A:** MVP uses **simulated `harga_pasar` inserts** on a schedule so comparison UI works. Live Bapanas/marketplace feeds are Post-MVP — we don’t claim live scrape today.

---

### Q: How do you prevent bad AI data?
**A:** Extract entities only → match products (exact → ILIKE → Jaccard) → stock check → **human YA** → atomic commit. Invalid / empty items never become VALID sales.

---

### Q: Government / SIMKOPDES access?
**A:** We **export** CSV/XLSX/JSON to MinIO + `ekspor_log`. We do **not** claim a direct write API to government systems.

---

### Q: What’s Post-MVP?
**A:** FCM push, offline TX queue, live price feeds, deeper federasi benchmarking, Meta Cloud swap. Not required for today’s demo.
