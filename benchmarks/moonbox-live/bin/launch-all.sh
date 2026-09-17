#!/bin/bash
# Daemon launcher — survives parent death via nohup + disown

BASE="/mnt/agents/output"
LOGS="$BASE/logs"
mkdir -p "$LOGS"

# Kill existing
pkill -9 -f 'envd-alt.py' 2>/dev/null
pkill -9 -f 'restarter-daemon' 2>/dev/null
pkill -9 -f 'tunnel-daemon' 2>/dev/null
pkill -9 -f 'vnc-tunnel' 2>/dev/null
sleep 1

# Launch with nohup — immune to SIGHUP
nohup python3 "$BASE/bin/envd-alt.py" > "$LOGS/envd-alt.log" 2>&1 &
disown

nohup python3 "$BASE/bin/restarter-daemon" > "$LOGS/restarter.log" 2>&1 &
disown

nohup python3 "$BASE/bin/tunnel-daemon" > "$LOGS/tunnel.log" 2>&1 &
disown

nohup python3 -c "
import http.server, socketserver
class P(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<iframe src=\"http://127.0.0.1:6080\" width=\"100%\" height=\"100%\" style=\"border:none\"></iframe>')
with socketserver.TCPServer(('0.0.0.0', 6081), P) as s:
    s.serve_forever()
" > "$LOGS/vnc-tunnel.log" 2>&1 &
disown

sleep 2

# Verify
echo "=== PIDs ==="
ps aux | grep -E 'envd-alt|restarter-daemon|tunnel-daemon|6081' | grep -v grep | grep -v bash

echo "=== PORTS ==="
for p in 18888 18889 18890 18891 6081; do
  nc -z -w 1 127.0.0.1 $p 2>/dev/null && echo ":$p OPEN" || echo ":$p CLOSED"
done
