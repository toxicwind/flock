#!/usr/bin/env python3
"""completions_racer.py — Race ALL Kimi AgentGW completions routes in parallel.

Targets: excessive route forging across all known gateways.
No rollback. Autohook fixes inline. Save all permanent.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

_script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(_script_dir))
from autohook import autohook, Autohook, race as autohook_race

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── SESSION ─────────────────────────────────────────────────────────────────
_session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504, 429])
_session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=100))
_session.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=100))

# ── GATEWAYS ────────────────────────────────────────────────────────────────
GATEWAYS = [
    ("PROD",    "https://agent-gw.kimi.com/coding"),
    ("DEV",     "https://agent-gw-dev.dev.kimi.team/coding"),
    ("SANDBOX", "https://kimi-api-sandbox.msh.team"),
    ("TEAM",    "https://kimi.kimi.team/apiv2"),
    ("CDN",     "https://cdn.kimi.com/agentgw/pysdk"),
]

# ── AUTH TOKENS (rotate through these) ──────────────────────────────────────
TOKENS = [
    os.environ.get("KIMI_API_KEY", ""),
    "sk-kimi-rHmZUSehP4Og8G3uvRYbkIMjUR71n33gobRU6UGKWBMlDnYQQs70mi6L0apkzqy4",
    "${GITHUB_PAT}",
]
TOKENS = [t for t in TOKENS if t]

# ── ROUTE MATRIX ────────────────────────────────────────────────────────────
def build_route_matrix() -> List[Tuple[str, str, str, dict, dict]]:
    """Build every (gateway, method, path, headers, body) combination."""
    routes = []
    
    for gw_name, gw_url in GATEWAYS:
        for token in TOKENS:
            base_h = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Kimi AgentGW PySDK/1.0",
            }
            
            # 1. GET /v1/models
            routes.append((f"{gw_name}_models", "GET", f"{gw_url}/v1/models", base_h, None))
            
            # 2. POST /v1/chat/completions (OpenAI compat)
            h2 = dict(base_h)
            h2["X-Kimi-Chat-Id"] = "19fecde7-2a92-857a-8000-095193e5fd48"
            routes.append((f"{gw_name}_chat_std", "POST", f"{gw_url}/v1/chat/completions", h2, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "temperature": 0.7,
            }))
            
            # 3. POST /v1/chat/completions with stream
            routes.append((f"{gw_name}_chat_stream", "POST", f"{gw_url}/v1/chat/completions", h2, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "count to 5"}],
                "stream": True,
            }))
            
            # 4. POST /v1/messages (Anthropic compat)
            routes.append((f"{gw_name}_messages", "POST", f"{gw_url}/v1/messages", h2, {
                "model": "claude-3-5-sonnet",
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 1024,
                "stream": False,
            }))
            
            # 5. POST /v1/messages/count_tokens
            routes.append((f"{gw_name}_count_tokens", "POST", f"{gw_url}/v1/messages/count_tokens", h2, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "test"}],
            }))
            
            # 6. POST /v1/embeddings
            routes.append((f"{gw_name}_embeddings", "POST", f"{gw_url}/v1/embeddings", h2, {
                "model": "kimi-embedding",
                "input": "test embedding text",
            }))
            
            # 7. POST /v1/search
            routes.append((f"{gw_name}_search", "POST", f"{gw_url}/v1/search", h2, {
                "text_query": "UAP skinwalker ranch plasma physics",
            }))
            
            # 8. POST /v1/fetch
            routes.append((f"{gw_name}_fetch", "POST", f"{gw_url}/v1/fetch", h2, {
                "url": "https://en.wikipedia.org/wiki/Skinwalker_Ranch",
            }))
            
            # 9. POST /v1/tools (stock price)
            routes.append((f"{gw_name}_tools_stock", "POST", f"{gw_url}/v1/tools", h2, {
                "method": "get_stock_realtime_price",
                "params": {"ticker": "AAPL.US", "time": "2026-08-11 09:30:00", "type": "realtime_price"},
            }))
            
            # 10. POST /v1/tools (data source desc)
            routes.append((f"{gw_name}_tools_datasource", "POST", f"{gw_url}/v1/tools", h2, {
                "method": "get_data_source_desc",
                "params": {"data_source_name": "yahoo_finance"},
            }))
            
            # 11. POST /v1/tools (generate image)
            routes.append((f"{gw_name}_tools_genimg", "POST", f"{gw_url}/v1/tools", h2, {
                "method": "generate_image",
                "params": {"description": "A glowing plasma orb over Skinwalker Ranch at night", "ratio": "16:9"},
            }))
            
            # 12. POST /v1/tools (web search)
            routes.append((f"{gw_name}_tools_websearch", "POST", f"{gw_url}/v1/tools", h2, {
                "method": "web_search",
                "params": {"queries": ["UAP AAWSAP AATIP Stratton Uintah Basin"]},
            }))
            
            # 13. POST /v1/storage (metadata probe — no actual upload)
            routes.append((f"{gw_name}_storage_meta", "GET", f"{gw_url}/v1/storage/nonexistent", h2, None))
            
            # 14. POST /v1/files (probe — no actual upload)
            routes.append((f"{gw_name}_files_probe", "POST", f"{gw_url}/v1/files", h2, {"purpose": "file-extract"}))
            
            # 15. Variant with skill header
            h3 = dict(base_h)
            h3["X-Kimi-Skill"] = "general"
            h3["X-Kimi-Chat-Id"] = "19fecde7-2a92-857a-8000-095193e5fd48"
            routes.append((f"{gw_name}_chat_skill", "POST", f"{gw_url}/v1/chat/completions", h3, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "hi with skill"}],
                "stream": False,
            }))
            
            # 16. Variant with device header
            h4 = dict(base_h)
            h4["X-Msh-Device"] = "web"
            h4["X-Kimi-Chat-Id"] = "19fecde7-2a92-857a-8000-095193e5fd48"
            routes.append((f"{gw_name}_chat_device", "POST", f"{gw_url}/v1/chat/completions", h4, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "hi with device"}],
                "stream": False,
            }))
            
            # 17. No chat_id variant
            h5 = dict(base_h)
            routes.append((f"{gw_name}_chat_nochatid", "POST", f"{gw_url}/v1/chat/completions", h5, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "no chat id"}],
                "stream": False,
            }))
            
            # 18. Wrong token variant (should 401)
            h6 = dict(base_h)
            h6["Authorization"] = "Bearer invalid_token_12345"
            routes.append((f"{gw_name}_chat_badauth", "POST", f"{gw_url}/v1/chat/completions", h6, {
                "model": "kimi-latest",
                "messages": [{"role": "user", "content": "bad auth"}],
                "stream": False,
            }))
            
            # 19. MCP probe
            routes.append((f"{gw_name}_mcp_init", "POST", f"{gw_url}/v1/mcp/", h2, {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
            }))
            
            # 20. CDN manifest
            routes.append((f"{gw_name}_cdn_manifest", "GET", f"{gw_url}/manifest.json", base_h, None))
    
    return routes

# ── FETCHER ─────────────────────────────────────────────────────────────────
@autohook(max_retries=5)
def forge_route(name: str, method: str, url: str, headers: dict, body: Any, timeout: float = 30.0) -> dict:
    """Forge a single route request with autohook recovery."""
    t0 = time.perf_counter()
    h = dict(headers) if headers else {}
    try:
        if method == "GET":
            resp = _session.get(url, headers=h, timeout=timeout)
        else:
            resp = _session.post(url, headers=h, json=body, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000
        
        # Try to parse body
        try:
            resp_body = resp.json()
        except ValueError:
            resp_body = resp.text[:2000]
        
        return {
            "name": name,
            "status": resp.status_code,
            "latency_ms": round(latency, 2),
            "body": resp_body,
            "headers": dict(resp.headers),
            "url": url,
            "method": method,
        }
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return {
            "name": name,
            "status": getattr(getattr(e, "response", None), "status_code", 0),
            "latency_ms": round(latency, 2),
            "error": str(e),
            "url": url,
            "method": method,
        }

# ── SAVE PERMANENT ──────────────────────────────────────────────────────────
def save_all(results: List[dict], prefix: str = "completions_race") -> Tuple[Path, Path]:
    BASE = _script_dir
    RECON = BASE / ".recon"
    PARQUET = BASE / ".parquet"
    RECON.mkdir(parents=True, exist_ok=True)
    PARQUET.mkdir(parents=True, exist_ok=True)
    
    ts = int(time.time())
    
    # JSON
    json_path = RECON / f"{prefix}_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Parquet
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        rows = []
        for r in results:
            if isinstance(r, dict) and not r.get("_autohook_error"):
                rows.append({
                    "name": r.get("name", ""),
                    "status": r.get("status", 0),
                    "latency_ms": r.get("latency_ms", 0),
                    "url": r.get("url", ""),
                    "method": r.get("method", ""),
                    "error": r.get("error", ""),
                    "body_preview": str(r.get("body", ""))[:500],
                })
            elif isinstance(r, dict):
                rows.append({
                    "name": r.get("_func", "unknown"),
                    "status": -1,
                    "latency_ms": 0,
                    "url": "",
                    "method": "",
                    "error": r.get("_exception", ""),
                    "body_preview": "",
                })
        if rows:
            df = pd.DataFrame(rows)
            parquet_path = PARQUET / f"{prefix}_{ts}.parquet"
            pq.write_table(pa.Table.from_pandas(df), str(parquet_path))
            return json_path, parquet_path
    except Exception as e:
        pass
    return json_path, None

# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("COMPLETIONS RACER — Forging ALL AgentGW routes in parallel")
    print("=" * 80)
    
    routes = build_route_matrix()
    print(f"\nTotal routes to race: {len(routes)}")
    print(f"Gateways: {len(GATEWAYS)}")
    print(f"Tokens: {len(TOKENS)}")
    print(f"Max workers: 64")
    
    # Build task list
    tasks = []
    for name, method, url, headers, body in routes:
        tasks.append((forge_route, (name, method, url, headers, body), {}))
    
    # RACE
    print("\n[GO] Racing all routes...")
    t0 = time.perf_counter()
    results = autohook_race(tasks, max_workers=64)
    total_ms = (time.perf_counter() - t0) * 1000
    
    ok = [r for r in results if isinstance(r, dict) and r.get("status", 0) in [200, 201, 204]]
    interesting = [r for r in results if isinstance(r, dict) and r.get("status", 0) not in [0, 200, 201, 204, 401, 403, 404]]
    auth_fail = [r for r in results if isinstance(r, dict) and r.get("status", 0) == 401]
    forbidden = [r for r in results if isinstance(r, dict) and r.get("status", 0) == 403]
    not_found = [r for r in results if isinstance(r, dict) and r.get("status", 0) == 404]
    timeouts = [r for r in results if isinstance(r, dict) and r.get("status", 0) == 0]
    
    print(f"\n{'='*80}")
    print(f"RACE COMPLETE in {total_ms:.0f}ms")
    print(f"{'='*80}")
    print(f"  ✓ 2xx Success:     {len(ok)}")
    print(f"  ! Interesting:     {len(interesting)}")
    print(f"  ✗ 401 Auth Fail:   {len(auth_fail)}")
    print(f"  ✗ 403 Forbidden:   {len(forbidden)}")
    print(f"  ✗ 404 Not Found:   {len(not_found)}")
    print(f"  ✗ Timeouts/Errors: {len(timeouts)}")
    
    # Show successes
    if ok:
        print(f"\n--- SUCCESSES (fastest 15) ---")
        for r in sorted(ok, key=lambda x: x["latency_ms"])[:15]:
            body_preview = str(r.get("body", ""))[:80]
            print(f"  ✓ {r['name']:45s} HTTP {r['status']}  {r['latency_ms']:8.1f}ms  {body_preview}")
    
    # Show interesting
    if interesting:
        print(f"\n--- INTERESTING (non-standard status) ---")
        for r in sorted(interesting, key=lambda x: x["latency_ms"])[:15]:
            body_preview = str(r.get("body", ""))[:80]
            print(f"  ! {r['name']:45s} HTTP {r['status']}  {r['latency_ms']:8.1f}ms  {body_preview}")
    
    # Show auth fails
    if auth_fail:
        print(f"\n--- 401 AUTH FAILS ---")
        for r in auth_fail[:10]:
            print(f"  ✗ {r['name']:45s} {r['latency_ms']:8.1f}ms")
    
    # Save
    print(f"\n[SAVING] Permanent storage...")
    json_path, parquet_path = save_all(results, "completions_race")
    print(f"  ✓ JSON:    {json_path}")
    if parquet_path:
        print(f"  ✓ Parquet: {parquet_path}")
    
    print(f"\n{'='*80}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
