#!/usr/bin/env python3
import urllib.request, json, sys

ENDPOINTS = {
    "restarter":    {"url": "http://127.0.0.1:18080/", "method": "GET"},
    "envd-alt":     {"url": "http://127.0.0.1:18888/", "method": "GET"},
    "kernel-tun":   {"url": "http://127.0.0.1:18889/", "method": "GET"},
    "restarter-tun":{"url": "http://127.0.0.1:18890/", "method": "GET"},
    "envd-tun":     {"url": "http://127.0.0.1:18891/", "method": "GET"},
    "kasmvnc":      {"url": "http://127.0.0.1:6080/", "method": "GET"},
    "vnc-iframe":   {"url": "http://127.0.0.1:6081/", "method": "GET"},
    "cdp":          {"url": "http://127.0.0.1:9223/json/version", "method": "GET"},
    "kernel":       {"url": "http://127.0.0.1:8888/", "method": "GET"},
}

results = {}
for name, cfg in ENDPOINTS.items():
    try:
        req = urllib.request.Request(cfg["url"], method=cfg["method"])
        req.add_header("User-Agent", "curl/7.68.0")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = resp.read(50).decode("utf-8", errors="ignore")
            results[name] = {"status": "LIVE", "preview": data[:40]}
    except Exception as e:
        results[name] = {"status": "DOWN", "error": str(e)[:30]}

print(json.dumps(results, indent=2))

# Exit code = number of dead services
dead = sum(1 for r in results.values() if r["status"] == "DOWN")
sys.exit(dead)
