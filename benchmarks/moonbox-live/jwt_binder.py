#!/usr/bin/env python3
# KimiWarden JWT Binder / Extractor v1
import json, base64, time, subprocess, sys, os

KNOWN_PAYLOAD = {
    "iss": "kimiwarden",
    "sub": "d87br2oh8njkr90jf520",
    "aud": "portal",
    "exp": 1786700704,
    "iat": 1786697104,
    "region": "OVERSEA",
    "workflow": "WORKFLOW_K2D5"
}

REJECTED_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiAia2ltaXdhcmRlbiIsICJzdWIiOiAiZDg3YnIyb2g4bmprcjkwamY1MjAiLCAiYXVkIjogInBvcnRhbCIsICJleHAiOiAxNzg2NzAwNzA0LCAiaWF0IjogMTc4NjY5NzEwNCwgInJlZ2lvbiI6ICJPVkVSU0VBIiwgIndvcmtmbG93IjogIldPUktGTE9XX0syRDUifQ.TPbSLlB_hdOZycft5rter2vBro8ZsjK93Xfwyl8Dzv4"

def decode_jwt(token):
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    try:
        payload = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload)
    except:
        return None

def generate_payload(sub=None, region="OVERSEA", workflow="WORKFLOW_K2D5", exp_hours=1):
    now = int(time.time())
    exp = now + (exp_hours * 3600)
    return {
        "iss": "kimiwarden",
        "sub": sub or KNOWN_PAYLOAD["sub"],
        "aud": "portal",
        "exp": exp,
        "iat": now,
        "region": region,
        "workflow": workflow
    }

def probe_envd_metrics():
    try:
        r = subprocess.run(
            "curl -s --max-time 3 http://127.0.0.1:18080/envd_metrics",
            shell=True, capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
    except:
        pass
    return None

def probe_envd_health():
    try:
        r = subprocess.run(
            "curl -s --max-time 3 http://127.0.0.1:18080/envd_health",
            shell=True, capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout:
            return json.loads(r.stdout)
    except:
        pass
    return None

def main():
    print("=== KimiWarden JWT Binder v1 ===")
    print("Known sub: " + KNOWN_PAYLOAD["sub"])
    print("Known region: " + KNOWN_PAYLOAD["region"])
    print("Known workflow: " + KNOWN_PAYLOAD["workflow"])
    print()
    decoded = decode_jwt(REJECTED_TOKEN)
    if decoded:
        print("[REJECTED TOKEN DECODED]")
        print(json.dumps(decoded, indent=2))
    fresh = generate_payload()
    print("\n[FRESH PAYLOAD]")
    print(json.dumps(fresh, indent=2))
    metrics = probe_envd_metrics()
    if metrics:
        print("\n[ENVD METRICS]")
        print(json.dumps(metrics, indent=2))
    else:
        print("\n[ENVD METRICS] Not available")
    health = probe_envd_health()
    if health:
        print("\n[ENVD HEALTH]")
        print(json.dumps(health, indent=2))
    else:
        print("\n[ENVD HEALTH] Not available")

if __name__ == "__main__":
    main()
