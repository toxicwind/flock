#!/usr/bin/env python3
"""
MAGIC — Multi-Autonomous Gateway & Infrastructure Controller
One script to rule all endpoints, auto-heal, and survive parent death.
"""
import subprocess, os, sys, time, json, urllib.request, signal

BASE = "/mnt/agents/output"
LOGS = f"{BASE}/logs"

SERVICES = {
    "envd-alt":     {"port": 18888, "cmd": ["python3", f"{BASE}/bin/envd-alt.py"], "log": "envd-alt.log"},
    "restarter":    {"port": 18080, "cmd": ["python3", f"{BASE}/bin/restarter-daemon"], "log": "restarter.log"},
    "tunnel":       {"port": None,   "cmd": ["python3", f"{BASE}/bin/tunnel-daemon"], "log": "tunnel.log"},
    "vnc-iframe":   {"port": 6081,  "cmd": ["python3", "-c", """
import http.server, socketserver
class P(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<iframe src=\"http://127.0.0.1:6080\" width=\"100%\" height=\"100%\" style=\"border:none\"></iframe>')
with socketserver.TCPServer(('0.0.0.0', 6081), P) as s:
    s.serve_forever()
"""], "log": "vnc-tunnel.log"},
}

def is_port_open(port):
    if port is None:
        return True
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
        with urllib.request.urlopen(req, timeout=1) as resp:
            return True
    except:
        return False

def start_service(name, cfg):
    log_path = f"{LOGS}/{cfg['log']}"
    proc = subprocess.Popen(
        cfg["cmd"],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc.pid

def kill_stale(name):
    subprocess.run(["pkill", "-9", "-f", name], capture_output=True)

def main():
    os.makedirs(LOGS, exist_ok=True)
    print(f"[{time.strftime('%H:%M:%S')}] MAGIC starting...")

    for name, cfg in SERVICES.items():
        if not is_port_open(cfg["port"]):
            print(f"  {name} down — restarting...")
            kill_stale(name)
            pid = start_service(name, cfg)
            print(f"  {name} PID {pid}")
        else:
            print(f"  {name} already live")

    print(f"[{time.strftime('%H:%M:%S')}] All services up.")

    # Auto-heal loop
    while True:
        time.sleep(5)
        for name, cfg in SERVICES.items():
            if cfg["port"] and not is_port_open(cfg["port"]):
                print(f"[{time.strftime('%H:%M:%S')}] {name} died — restarting...")
                kill_stale(name)
                pid = start_service(name, cfg)
                print(f"  {name} PID {pid}")

if __name__ == "__main__":
    main()
