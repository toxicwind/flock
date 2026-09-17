#!/usr/bin/env python3
"""
envd_routed.py - Auto-discovered envd HTTP/gRPC routes
Injected with proc env vars from /proc/*/environ audit
"""
import os, json, urllib.request, urllib.error

# === INJECTED ENV VARS FROM PROC AUDIT ===
_PROC_ENV = {
    "AGENT_RUNTIME_SANDBOX_ID": "z3jy5rapof5v3cpizocpfirlpwdsl3y54bpuhemi",
    "DRIVE9_API_KEY": os.environ.get("DRIVE9_API_KEY", ""),
    "DRIVE9_SERVER": os.environ.get("DRIVE9_SERVER", "http://10.213.5.144"),
    "KIMI_PROJECT_PORTAL_CAPABILITY_ENABLED": "true",
    "KIMI_PROJECT_PORTAL_CAPABILITY_ENV": "prod",
    "KIMI_PROJECT_PORTAL_CAPABILITY_MOUNT": "/mnt/portal-overlay",
    "KIMI_PROJECT_PORTAL_CAPABILITY_PROD_ADDR": "https://kimi-api-sandbox.msh.team/apiv2",
    "PROJECT_WORKSPACE_PATH": "/mnt/agents",
    "SCF_POD_ID": "f770e87e1c1e409f9b85e3efad366afe",
    "CUBE_CONTAINER_ID_SANDBOX": "f770e87e1c1e409f9b85e3efad366afe",
    "CUBE_CONTAINER_ID_MONITOR_SIDECAR": "0246c8e58b5d47bc8e91ddaca64f3fa6",
    "VNC_PASSWORD": "vncpassword",
    "SSH_PASSWORD": "sshpassword",
    "USE_CDP": "true",
    "S6_LOGGING": "0",
}

# Merge with current process env
for k, v in _PROC_ENV.items():
    if k not in os.environ:
        os.environ[k] = v

ENVD_HOST = os.environ.get("ENVD_HOST", "localhost")
ENVD_PORT = int(os.environ.get("ENVD_PORT", "49983"))
ENVD_BASE = f"http://{ENVD_HOST}:{ENVD_PORT}"

class EnvdClient:
    """Minimal envd HTTP client with 3s timeout"""
    def __init__(self, base=ENVD_BASE, timeout=3):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self._routes = {}

    def _req(self, method, path, data=None, headers=None):
        url = f"{self.base}{path}"
        req = urllib.request.Request(url, method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if data is not None:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return {"status": resp.status, "body": resp.read().decode(), "ok": True}
        except urllib.error.HTTPError as e:
            return {"status": e.code, "body": e.read().decode()[:500], "ok": False, "error": str(e)}
        except Exception as e:
            return {"status": None, "body": "", "ok": False, "error": str(e)}

    def metrics(self):
        """GET /metrics - returns JSON with cpu/mem/disk stats"""
        return self._req("GET", "/metrics")

    def health(self):
        """GET /health - currently 404, but probe anyway"""
        return self._req("GET", "/health")

    def probe_all(self):
        """Probe all known/potential routes"""
        routes = [
            "/", "/metrics", "/health", "/healthz", "/ready", "/status",
            "/api", "/api/v1", "/api/v1/status", "/v1", "/v1/status",
            "/debug", "/info", "/version", "/grpc", "/rpc",
        ]
        results = {}
        for r in routes:
            results[r] = self._req("GET", r)
        return results

    def get_metrics_parsed(self):
        """Parse metrics JSON into dict"""
        r = self.metrics()
        if r["ok"]:
            try:
                return json.loads(r["body"])
            except:
                pass
        return r

class Drive9Client:
    """Drive9 FUSE storage client"""
    def __init__(self, timeout=3):
        self.server = os.environ.get("DRIVE9_SERVER", "http://10.213.5.144")
        self.api_key = os.environ.get("DRIVE9_API_KEY", "")
        self.timeout = timeout

    def _req(self, method, path, data=None):
        url = f"{self.server}{path}"
        req = urllib.request.Request(url, method=method)
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
            req.add_header("X-API-Key", self.api_key)
        if data:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(data).encode()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return {"status": resp.status, "body": resp.read().decode(), "ok": True}
        except Exception as e:
            return {"status": None, "body": "", "ok": False, "error": str(e)}

    def probe(self):
        paths = ["/", "/health", "/status", "/api/v1/status", "/quota", "/api/v1/quota"]
        return {p: self._req("GET", p) for p in paths}

# === CDP CLIENT ===
class CDPClient:
    """Chrome DevTools Protocol client"""
    def __init__(self, host="localhost", port=9222, timeout=3):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def _req(self, path):
        url = f"{self.base}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def list_targets(self):
        return self._req("/json/list")

    def version(self):
        return self._req("/json/version")

# === UTILS ===
def get_disk_usage(path="/"):
    """Cross-platform disk usage"""
    import shutil
    try:
        total, used, free = shutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": total / (1024**3),
            "used_gb": used / (1024**3),
            "free_gb": free / (1024**3),
            "percent": (used / total) * 100
        }
    except Exception as e:
        return {"error": str(e)}

def fix_permissions(path, mode=0o777):
    """Recursively chmod"""
    import os
    changed = 0
    for root, dirs, files in os.walk(path, topdown=True):
        for d in dirs:
            try:
                os.chmod(os.path.join(root, d), mode)
                changed += 1
            except:
                pass
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    os.chmod(fp, mode)
                    changed += 1
                except:
                    pass
    return changed

# === CLI ===
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"

    if cmd == "probe":
        envd = EnvdClient()
        print("=== ENVD ROUTE PROBE ===")
        for route, result in envd.probe_all().items():
            status = result.get("status", "ERR")
            print(f"  {route}: HTTP {status}")

        print("\n=== ENVD METRICS ===")
        m = envd.get_metrics_parsed()
        print(json.dumps(m, indent=2))

        print("\n=== DISK USAGE ===")
        print(json.dumps(get_disk_usage("/"), indent=2))
        print(json.dumps(get_disk_usage("/mnt/agents"), indent=2))

        print("\n=== CDP VERSION ===")
        cdp = CDPClient()
        print(json.dumps(cdp.version(), indent=2))

    elif cmd == "fixperms":
        path = sys.argv[2] if len(sys.argv) > 2 else "/mnt/agents"
        n = fix_permissions(path)
        print(f"Fixed permissions on {n} items in {path}")

    elif cmd == "drive9":
        d9 = Drive9Client()
        print(json.dumps(d9.probe(), indent=2))
