#!/bin/bash
# SOVEREIGN TELEMETRY BLOCKLIST
# Install: sudo bash /mnt/agents/output/blocklist.sh
# Removes: Volces gator, Baidu, Google Analytics, Intercom, Cloudflare insights

echo "[+] Installing sovereign telemetry blocklist..."

BLOCKLIST="
# === SOVEREIGN TELEMETRY BLOCKLIST ===
# Generated from HAR analysis - 2026-08-15
0.0.0.0 gator.volces.com
0.0.0.0 apmplus.volces.com
0.0.0.0 tab.volces.com
0.0.0.0 sg-fp.apitd.net
0.0.0.0 static.trustdecision.com
0.0.0.0 hm.baidu.com
0.0.0.0 analytics.google.com
0.0.0.0 www.googletagmanager.com
0.0.0.0 static.cloudflareinsights.com
0.0.0.0 js.intercomcdn.com
0.0.0.0 api-iam.intercom.io
0.0.0.0 widget.intercom.io
0.0.0.0 cdn-cgi.rum.cloudflare.com
"

# Check if already installed
if grep -q "SOVEREIGN TELEMETRY BLOCKLIST" /etc/hosts; then
    echo "[!] Blocklist already installed. Updating..."
    # Remove old blocklist
    sed -i '/# === SOVEREIGN TELEMETRY BLOCKLIST ===/,/# === END SOVEREIGN BLOCKLIST ===/d' /etc/hosts
fi

# Append blocklist
cat >> /etc/hosts << EOF
${BLOCKLIST}
# === END SOVEREIGN BLOCKLIST ===
EOF

echo "[+] Blocklist installed. $(echo "$BLOCKLIST" | grep -c '0.0.0.0') domains blocked."
echo "[+] Verify: grep gator.volces.com /etc/hosts"
