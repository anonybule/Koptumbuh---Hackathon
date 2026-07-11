# Demo readiness (Windows PowerShell) — Path B POS, no WhatsApp
$ErrorActionPreference = "Stop"
$Base = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8100" }
$Api = "$Base/api/v1"
$Pass = 0
$Fail = 0

function Ok($m) { Write-Host "  PASS: $m"; $script:Pass++ }
function Bad($m, $d) { Write-Host "  FAIL: $m — $d"; $script:Fail++ }

Write-Host "=== DEMO READY (Path B: POS) ==="

try {
  $health = Invoke-RestMethod -Uri "$Base/health" -Method Get
  Ok "health reachable ($($health.status))"
} catch {
  Bad "health" $_.Exception.Message
  Write-Host "=== RESULTS: $Pass passed, $Fail failed ==="
  exit 1
}

try {
  $login = Invoke-RestMethod -Uri "$Api/auth/login" -Method Post -ContentType "application/json" `
    -Body '{"phone":"628123456003","password":"kop123"}'
  $token = $login.data.access_token
  if (-not $token) { throw "no token" }
  Ok "login 628123456003"
} catch {
  Bad "login" $_.Exception.Message
  exit 1
}

$headers = @{ Authorization = "Bearer $token" }
$inv = Invoke-RestMethod -Uri "$Api/admin/inventory?per_page=50" -Headers $headers
$item = $inv.data | Where-Object { [double]$_.stock -ge 1 } | Select-Object -First 1
if (-not $item) {
  Bad "inventory" "no product with stock>=1"
  exit 1
}
Ok "inventory pick: $($item.name) ($($item.id))"

$body = @{
  customer_name = "Demo Juri"
  payment_method = "Cash"
  line_items = @(@{ produk_sample_id = $item.id; quantity = 1 })
} | ConvertTo-Json -Depth 5

try {
  $sale = Invoke-RestMethod -Uri "$Api/admin/pos/transactions" -Method Post -Headers $headers -ContentType "application/json" -Body $body
  $tx = $sale.data.transaksi_sample_id
  if (-not $tx) { $tx = $sale.data.id }
  if (-not $tx) { throw "no tx id" }
  Ok "POS sale $tx"
} catch {
  Bad "pos sale" $_.Exception.Message
  exit 1
}

$txlist = Invoke-RestMethod -Uri "$Api/admin/transactions" -Headers $headers
$found = $txlist.data | Where-Object { $_.id -eq $tx -or $_.transaksi_sample_id -eq $tx }
if ($found) { Ok "transaction visible in admin list" } else { Bad "transaction list" "new TX not found" }

$kpi = Invoke-RestMethod -Uri "$Api/admin/dashboard/kpi" -Headers $headers
if ($kpi.success) { Ok "dashboard KPI" } else { Bad "kpi" "success=false" }

Write-Host ""
Write-Host "=== RESULTS: $Pass passed, $Fail failed ==="
Write-Host "Next: open http://localhost:3000 (or :8101) → Dashboard (demo mode skips login)"
Write-Host "TX id: $tx"
if ($Fail -gt 0) { exit 1 }
