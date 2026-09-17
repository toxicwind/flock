#!/bin/bash
# core.sh — Core infrastructure: envd-alt, portal, sandbox management

ENVD_ALT="http://127.0.0.1:18888"

envd_status() {
    curl -s -m 2 "$ENVD_ALT" > /dev/null 2>&1 && echo "RUNNING" || echo "DOWN"
}

envd_restart() {
    pkill -f envd-alt 2>/dev/null || true
    nohup python3 /mnt/agents/output/bin/envd-alt.py > /tmp/envd-alt.log 2>&1 &
    sleep 1
    envd_status
}

envd_exec() {
    local cmd="$1"
    curl -s -m 60 -X POST "$ENVD_ALT/" \
      -H "Content-Type: application/json" \
      -d "{\"cmd\":\"$cmd\"}" 2>/dev/null
}

portal_status() {
    pgrep -f "/usr/local/bin/portal" > /dev/null 2>&1 && echo "RUNNING" || echo "DOWN"
}

portal_connections() {
    cat /proc/71/net/tcp 2>/dev/null | python3 -c "
import sys
for line in sys.stdin:
    parts = line.split()
    if len(parts) >= 4:
        rem = parts[2]
        try:
            rem_ip = ..join(str(int(rem[i:i+2],16)) for i in (6,4,2,0))
            rem_port = int(rem[9:], 16)
            print(f\"Remote: {rem_ip}:{rem_port}\")
        except:
            pass
"
}
