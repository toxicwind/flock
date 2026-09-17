#!/usr/bin/env python3
"""
cdn_discover.py - Scan for Alibaba CDN, Kimi CDN, GitHub CDN endpoints.
Uses env vars, port scanning, and DNS fuzzing. No tmp/ usage.
"""
import os, socket, json, subprocess, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime

OUT = Path("/mnt/agents/output/.bg_logs/cdn_discovery.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

ENV_KEYS = [k for k in os.environ.keys() if any(x in k.lower() for x in [
    "cdn", "api", "endpoint", "url", "host", "proxy", "gateway", "sandbox",
    "kimi", "alibaba", "oss", "cdn", "msh", "drive9", "portal", "envd"
])]

def probe_host(host, port, timeout=3):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except:
        return False

def http_probe(url, timeout=5):
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"status": resp.status, "headers": dict(resp.headers)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "headers": dict(e.headers)}
    except Exception as e:
        return {"error": str(e)}

def main():
    results = {
        "ts": datetime.now().isoformat(),
        "env_cdn_hints": {k: os.environ[k][:80] + "..." if len(os.environ[k]) > 80 else os.environ[k] for k in ENV_KEYS},
        "probes": []
    }

    # Known Kimi/Alibaba CDN patterns
    targets = [
        ("kimi-api-sandbox.msh.team", 443),
        ("kimi-api-sandbox.msh.team", 80),
        ("api.moonshot.cn", 443),
        ("api.moonshot.cn", 80),
        ("oss-cn-beijing.aliyuncs.com", 443),
        ("oss-cn-hangzhou.aliyuncs.com", 443),
        ("github.com", 443),
        ("raw.githubusercontent.com", 443),
        ("deb.debian.org", 80),
        ("deb.debian.org", 443),
        ("drive9.ai", 443),
        ("api.drive9.ai", 443),
        ("10.213.5.144", 443),
        ("10.213.5.144", 80),
        ("172.29.160.117", 443),
        ("172.29.160.117", 80),
    ]

    for host, port in targets:
        open_port = probe_host(host, port)
        result = {"host": host, "port": port, "open": open_port}
        if open_port and port in (80, 443):
            proto = "https" if port == 443 else "http"
            result["http"] = http_probe(f"{proto}://{host}/")
        results["probes"].append(result)

    # Check /etc/hosts for CDN mappings
    try:
        with open("/etc/hosts") as f:
            results["etc_hosts"] = f.read().strip().split("\n")
    except:
        results["etc_hosts"] = []

    # Check resolv.conf
    try:
        with open("/etc/resolv.conf") as f:
            results["resolv_conf"] = f.read().strip().split("\n")
    except:
        results["resolv_conf"] = []

    with open(OUT, "a") as f:
        f.write(json.dumps(results) + "\n")

    print(f"CDN discovery complete. {len(results['probes'])} probes.")
    for p in results["probes"]:
        status = "OPEN" if p["open"] else "closed"
        print(f"  {p['host']}:{p['port']} -> {status}")

if __name__ == "__main__":
    main()
