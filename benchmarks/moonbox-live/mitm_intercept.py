from mitmproxy import http
import json, os

LOG_FILE = "/mnt/agents/output/mitm_requests.log"

def request(flow: http.HTTPFlow) -> None:
    with open(LOG_FILE, "a") as f:
        f.write(f"REQ {flow.request.method} {flow.request.url}\n")
        for k, v in flow.request.headers.items():
            if any(x in k.lower() for x in ["auth", "token", "key", "cookie", "x-"]):
                f.write(f"  HDR {k}: {v[:100]}\n")
        if flow.request.content:
            f.write(f"  BODY {flow.request.content[:200]}\n")

def response(flow: http.HTTPFlow) -> None:
    with open(LOG_FILE, "a") as f:
        f.write(f"RESP {flow.response.status_code} {flow.request.url}\n")
        f.write(f"  BODY {flow.response.content[:200]}\n")
        f.write("---\n")
