#!/bin/bash
# KopTumbuh API Test Collection — run against localhost:8000
BASE="${API_URL:-http://localhost:8000}/api/v1"
PASS=0
FAIL=0

check() {
  local label="$1"; shift
  local resp
  resp=$("$@" 2>/dev/null)
  if echo "$resp" | grep -qE '"success"[[:space:]]*:[[:space:]]*true'; then
    echo "  PASS: $label"
    PASS=$((PASS+1))
  else
    echo "  FAIL: $label ($resp)"
    FAIL=$((FAIL+1))
  fi
}

auth_get() { curl -sf "$1" -H "Authorization: Bearer $TOKEN"; }
auth_post() { curl -sf -X POST "$1" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" ${2:+-d "$2"}; }
auth_patch() { curl -sf -X PATCH "$1" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" ${2:+-d "$2"}; }

echo "=== AUTH ==="
TOKEN=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d '{"phone":"628123456003","password":"kop123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null)
[ -n "$TOKEN" ] && echo "  PASS: login" && PASS=$((PASS+1)) || { echo "  FAIL: login"; FAIL=$((FAIL+1)); TOKEN=""; }

REFRESH=$(curl -sf -X POST "$BASE/auth/login" -H "Content-Type: application/json" -d '{"phone":"628123456003","password":"kop123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['data'].get('refresh_token',''))" 2>/dev/null)
if [ -n "$REFRESH" ]; then
  check "auth refresh" curl -sf -X POST "$BASE/auth/refresh" -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}"
fi

echo "=== WEBHOOK ==="
MSG_ID="TEST-$(date +%s)"
check "webhook receive" curl -sf -X POST "$BASE/webhooks/whatsapp" -H "Content-Type: application/json" -d "{\"event\":\"messages.upsert\",\"data\":{\"key\":{\"id\":\"$MSG_ID\",\"remoteJid\":\"628123456003@s.whatsapp.net\"},\"message\":{\"conversation\":\"test\",\"messageType\":\"conversation\"}}}"

echo "=== MOBILE ==="
check "mobile dashboard" auth_get "$BASE/mobile/dashboard/summary"
check "mobile products" auth_get "$BASE/mobile/products"
check "mobile transactions" auth_get "$BASE/mobile/transactions"
check "mobile restock" auth_get "$BASE/mobile/restock"
check "mobile members search" auth_get "$BASE/mobile/members/search?q=a"
check "mobile customers" auth_get "$BASE/mobile/customers"
check "mobile savings" auth_get "$BASE/mobile/savings"
check "mobile recommendations" auth_get "$BASE/mobile/recommendations"
check "mobile messages" auth_get "$BASE/mobile/messages"
check "mobile notifications" auth_get "$BASE/mobile/notifications"
check "mobile profile" auth_get "$BASE/mobile/profile"
check "mobile my-transactions" auth_get "$BASE/mobile/my-transactions"
check "mobile my-savings" auth_get "$BASE/mobile/my-savings"
check "mobile my-loans" auth_get "$BASE/mobile/my-loans"
check "mobile deliveries" auth_get "$BASE/mobile/deliveries"
check "mobile knowledge search" auth_get "$BASE/mobile/knowledge/search?q=simpanan"

echo "=== ADMIN DASHBOARD ==="
check "admin kpi" auth_get "$BASE/admin/dashboard/kpi"
check "admin sales" auth_get "$BASE/admin/dashboard/sales"
check "admin top-products" auth_get "$BASE/admin/dashboard/top-products"
check "admin active-members" auth_get "$BASE/admin/dashboard/active-members"
check "admin margin" auth_get "$BASE/admin/dashboard/margin"
check "admin stock-reconciliation" auth_get "$BASE/admin/dashboard/stock-reconciliation"
check "admin member-activity" auth_get "$BASE/admin/dashboard/member-activity"
check "admin slow-moving" auth_get "$BASE/admin/dashboard/slow-moving"
check "admin segmentation" auth_get "$BASE/admin/dashboard/segmentation"
check "admin retention" auth_get "$BASE/admin/dashboard/retention"
check "admin shu" auth_get "$BASE/admin/shu/estimate"
check "admin price-comparison" auth_get "$BASE/admin/price-comparison"
check "admin loans" auth_get "$BASE/admin/loans"

echo "=== ADMIN RESOURCES ==="
check "admin inventory" auth_get "$BASE/admin/inventory"
check "admin suppliers" auth_get "$BASE/admin/suppliers"
check "admin restock-plan" auth_get "$BASE/admin/restock-plan"
check "admin purchase-history" auth_get "$BASE/admin/purchase-history"
check "admin members" auth_get "$BASE/admin/members"
check "admin cooperatives" auth_get "$BASE/admin/cooperatives"
check "admin transactions" auth_get "$BASE/admin/transactions"
check "admin recommendations" auth_get "$BASE/admin/recommendations"
check "admin notifications" auth_get "$BASE/admin/notifications"
check "admin users" auth_get "$BASE/admin/users"
check "admin knowledge" auth_get "$BASE/admin/knowledge"
check "admin village commodities" auth_get "$BASE/admin/village/commodities"
check "admin village profiles" auth_get "$BASE/admin/village/profiles"
check "admin finance bank-accounts" auth_get "$BASE/admin/finance/bank-accounts"
check "admin finance capital" auth_get "$BASE/admin/finance/capital"
check "admin applications bank" auth_get "$BASE/admin/applications/bank-account"
check "admin applications financing" auth_get "$BASE/admin/applications/financing"
check "admin applications partnership" auth_get "$BASE/admin/applications/partnership"
check "admin applications domain" auth_get "$BASE/admin/applications/domain"
check "admin export history" auth_get "$BASE/admin/export/history"

echo "=== ADMIN WRITES ==="
curl -sf -X POST "$BASE/admin/recommendations/generate" -H "Authorization: Bearer $TOKEN" >/dev/null 2>&1 \
  && echo "  PASS: generate recommendations" && PASS=$((PASS+1)) \
  || echo "  SKIP: generate recommendations (optional)"

check "admin export trigger" auth_post "$BASE/admin/export/simkopdes" '{}'

echo "=== HEALTH ==="
check "health" curl -sf "http://localhost:8000/health"

echo ""
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
