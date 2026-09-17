#!/usr/bin/env python3
"""cdn_wrapper_v2.py - Fast mirror selection from live data."""
import socket, time, json, os

MIRRORS = {
    "kimi_api": {"host": "kimi-api-sandbox.msh.team", "port": 443, "type": "api"},
    "agent_gw": {"host": "agent-gw.kimi.com", "port": 443, "type": "api"},
    "drive9": {"host": "drive9.ai", "port": 443, "type": "storage"},
    "jsdelivr": {"host": "cdn.jsdelivr.net", "port": 443, "type": "cdn"},
    "pypi": {"host": "files.pythonhosted.org", "port": 443, "type": "package"},
    "npm": {"host": "registry.npmjs.org", "port": 443, "type": "package"},
}

def probe(host, port, timeout=2):
    t0 = time.time()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return round((time.time() - t0) * 1000, 2)
    except:
        return 9999

def get_fastest(category=None):
    results = {}
    for name, cfg in MIRRORS.items():
        if category and cfg.get("type") != category:
            continue
        results[name] = probe(cfg["host"], cfg["port"])
    fastest = min(results, key=results.get)
    return fastest, results[fastest], results

def github_api(path, token=None):
    token = token or os.environ.get("GITHUB_PAT", "")
    import urllib.request
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    fastest, latency, all_results = get_fastest()
    print(f"§FASTEST§ {fastest} @ {latency}ms")
    for name, ms in sorted(all_results.items(), key=lambda x: x[1]):
        print(f"  {name}: {ms}ms")
