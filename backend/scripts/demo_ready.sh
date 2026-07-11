#!/bin/bash
# Demo readiness: health → login → POS sale → verify TX (no WhatsApp required)
set -e
BASE="${API_URL:-http://localhost:8100}"
API="$BASE/api/v1"
PASS=0
FAIL=0

ok() { echo "  PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1 — $2"; FAIL=$((FAIL+1)); }

echo "=== DEMO READY (Path B: POS) ==="

HEALTH=$(curl -sf "$BASE/health" 2>/dev/null || true)
if echo "$HEALTH" | grep -q '"db"'; then
  ok "health reachable"
  echo "       $HEALTH"
else
  bad "health" "Is API up on $BASE ?"
  echo "=== RESULTS: $PASS passed, $FAIL failed ==="
  exit 1
fi

LOGIN=$(curl -sf -X POST "$API/auth/login" -H "Content-Type: application/json" \
  -d '{"phone":"628123456003","password":"kop123"}' 2>/dev/null || true)
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
  bad "login" "seed user missing? $LOGIN"
  echo "=== RESULTS: $PASS passed, $FAIL failed ==="
  exit 1
fi
ok "login 628123456003"

AUTH="Authorization: Bearer $TOKEN"
INV=$(curl -sf "$API/admin/inventory?per_page=50" -H "$AUTH" 2>/dev/null || true)
PROD=$(echo "$INV" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('data') or []
for i in d:
  if float(i.get('stock') or 0) >= 1:
    print(i['id']); print(i.get('name','')); break
" 2>/dev/null || true)
PROD_ID=$(echo "$PROD" | sed -n '1p')
PROD_NAME=$(echo "$PROD" | sed -n '2p')
if [ -z "$PROD_ID" ]; then
  bad "inventory" "no product with stock>=1"
  exit 1
fi
ok "inventory pick: $PROD_NAME ($PROD_ID)"

SALE=$(curl -sf -X POST "$API/admin/pos/transactions" -H "$AUTH" -H "Content-Type: application/json" \
  -d "{\"customer_name\":\"Demo Juri\",\"payment_method\":\"Cash\",\"line_items\":[{\"produk_sample_id\":\"$PROD_ID\",\"quantity\":1}]}" 2>/dev/null || true)
TX=$(echo "$SALE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('transaksi_sample_id') or d.get('data',{}).get('id') or '')" 2>/dev/null || true)
if [ -z "$TX" ]; then
  bad "pos sale" "$SALE"
  exit 1
fi
ok "POS sale $TX"

TXLIST=$(curl -sf "$API/admin/transactions" -H "$AUTH" 2>/dev/null || true)
if echo "$TXLIST" | grep -q "$TX"; then
  ok "transaction visible in admin list"
else
  bad "transaction list" "new TX not found"
fi

KPI=$(curl -sf "$API/admin/dashboard/kpi" -H "$AUTH" 2>/dev/null || true)
if echo "$KPI" | grep -q '"success"[[:space:]]*:[[:space:]]*true'; then
  ok "dashboard KPI"
else
  bad "kpi" "$KPI"
fi

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
echo "Next: open http://localhost:3000 (or :8101) → Dashboard (demo mode skips login)"
echo "TX id: $TX"
[ "$FAIL" -eq 0 ]
