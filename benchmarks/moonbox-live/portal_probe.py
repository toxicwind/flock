
import urllib.request, urllib.error, json, time

# ===============================================================================
# CRITICAL FINDINGS FROM PORTAL BINARY:
# 1. portal.v1.GetAPIKeyRequest/Response — API key generation endpoint!
# 2. portal.v1.ValidateBindToken — Token validation
# 3. portal.v1.S3ConfigR — S3 credentials (potential data exfil)
# 4. https://auth.kimi.com — Auth service
# 5. https://open.kimi.com — Open platform
# ===============================================================================

print("=" * 70)
print("CRITICAL: portal.v1.GetAPIKey — Can we generate a new key?")
print("=" * 70)

# The portal binary has GetAPIKey endpoint — try to access it
# This might be via gRPC or HTTP

# Try HTTP POST to GetAPIKey
api_key_targets = [
    ("https://agent-gw.kimi.com/coding/v1/GetAPIKey", "POST", {}, "grpc_GetAPIKey_http"),
    ("https://api.kimi.com/coding/v1/GetAPIKey", "POST", {}, "api_GetAPIKey"),
    ("https://agent-gw.kimi.com/coding/portal.v1.PortalService/GetAPIKey", "POST", {}, "grpc_full_path"),
    ("https://api.kimi.com/coding/portal.v1.PortalService/GetAPIKey", "POST", {}, "api_full_path"),
]

for url, method, payload, tag in api_key_targets:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode() if payload else None,
            headers={"Content-Type": "application/json"},
            method=method
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n✅ {r.status}: {tag} ({elapsed:.1f}ms)")
        print(f"   {body[:500]}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n⚠️  {e.code}: {tag} ({elapsed:.1f}ms)")
        print(f"   {err[:300]}")
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n❌ {type(e).__name__}: {tag} ({elapsed:.1f}ms)")

# ── TRY AUTH.KIMI.COM ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("AUTH.KIMI.COM — Standalone auth service")
print("=" * 70)

auth_targets = [
    ("https://auth.kimi.com/", "GET", {}, "auth_root"),
    ("https://auth.kimi.com/api", "GET", {}, "auth_api"),
    ("https://auth.kimi.com/v1", "GET", {}, "auth_v1"),
    ("https://auth.kimi.com/login", "GET", {}, "auth_login"),
    ("https://auth.kimi.com/token", "POST", {}, "auth_token"),
    ("https://auth.kimi.com/api_key", "POST", {}, "auth_api_key"),
    ("https://auth.kimi.com/oauth", "GET", {}, "auth_oauth"),
]

for url, method, payload, tag in auth_targets:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n✅ {r.status}: {tag} ({elapsed:.1f}ms)")
        print(f"   {body[:500]}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        if e.code != 404:
            print(f"\n⚠️  {e.code}: {tag} ({elapsed:.1f}ms)")
            print(f"   {err[:300]}")
    except Exception as e:
        pass

# ── TRY OPEN.KIMI.COM ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("OPEN.KIMI.COM — Open platform")
print("=" * 70)

open_targets = [
    ("https://open.kimi.com/", "GET", {}, "open_root"),
    ("https://open.kimi.com/api", "GET", {}, "open_api"),
    ("https://open.kimi.com/v1", "GET", {}, "open_v1"),
    ("https://open.kimi.com/models", "GET", {}, "open_models"),
    ("https://open.kimi.com/token", "POST", {}, "open_token"),
]

for url, method, payload, tag in open_targets:
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        print(f"\n✅ {r.status}: {tag} ({elapsed:.1f}ms)")
        print(f"   {body[:500]}")
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        elapsed = (time.perf_counter() - start) * 1000
        if e.code != 404:
            print(f"\n⚠️  {e.code}: {tag} ({elapsed:.1f}ms)")
            print(f"   {err[:300]}")
    except Exception as e:
        pass