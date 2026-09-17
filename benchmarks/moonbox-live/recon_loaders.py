#!/usr/bin/env python3
"""recon_loaders — Autohook-powered reconnaissance loaders.

Imports autohook.py maximally. No repeated code.
Loads parquet intel, GitHub data, drive9 metadata, saves permanent.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── IMPORT AUTOHOOK (maximal reuse, no repeat code) ─────────────────────────
_script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(_script_dir))
from autohook import Autohook, autohook, register_fix, race as autohook_race

# ── IMPORT AGENT GW CLIENT (maximal reuse) ──────────────────────────────────
from agent_gw_client import AgentGwClient, APIError

# ── CONSTANTS ───────────────────────────────────────────────────────────────
BASE = _script_dir
PARQUET_DIR = BASE / ".parquet"
RECON_DIR = BASE / ".recon"
LOG_DIR = BASE / ".bg_logs"
DRIVE9_DIR = BASE / "drive9"
for d in [PARQUET_DIR, RECON_DIR, LOG_DIR, DRIVE9_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PAT = "${GITHUB_PAT}"
GH_HEADERS = {
    "Authorization": f"Bearer {PAT}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "recon-loader/1.0",
}
GH_BASE = "https://api.github.com"

# ── SESSION (shared, reused) ────────────────────────────────────────────────
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504, 429])
_session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=50))
_session.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=50))

# ── PARQUET LOADER ──────────────────────────────────────────────────────────
@autohook(max_retries=3)
def load_all_parquet() -> Dict[str, Any]:
    """Load all .parquet files from PARQUET_DIR and subdirs."""
    intel = {}
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {"_autohook_error": True, "_exception": "pyarrow not installed"}
    for p in sorted(PARQUET_DIR.rglob("*.parquet")):
        try:
            table = pq.read_table(str(p))
            df = table.to_pandas()
            intel[p.name] = {"rows": len(df), "cols": list(df.columns), "df": df}
        except Exception as e:
            intel[p.name] = {"error": str(e)}
    for p in sorted(DRIVE9_DIR.rglob("*.parquet")):
        try:
            table = pq.read_table(str(p))
            df = table.to_pandas()
            intel[f"drive9_{p.name}"] = {"rows": len(df), "cols": list(df.columns), "df": df}
        except Exception as e:
            intel[f"drive9_{p.name}"] = {"error": str(e)}
    return intel

# ── GITHUB ROUTE DEFINITIONS ────────────────────────────────────────────────
GH_ROUTES = [
    ("gh_user",              "GET", f"{GH_BASE}/user"),
    ("gh_user_repos",        "GET", f"{GH_BASE}/user/repos?per_page=100"),
    ("gh_user_orgs",         "GET", f"{GH_BASE}/user/orgs"),
    ("gh_user_emails",       "GET", f"{GH_BASE}/user/emails"),
    ("gh_user_keys",         "GET", f"{GH_BASE}/user/keys"),
    ("gh_user_gists",        "GET", f"{GH_BASE}/gists"),
    ("gh_user_starred",      "GET", f"{GH_BASE}/user/starred"),
    ("gh_user_subscriptions","GET", f"{GH_BASE}/user/subscriptions"),
    ("gh_user_teams",        "GET", f"{GH_BASE}/user/teams"),
    ("gh_user_issues",       "GET", f"{GH_BASE}/issues?filter=all&state=all&per_page=100"),
    ("gh_user_notifications","GET", f"{GH_BASE}/notifications?per_page=100"),
    ("gh_rate_limit",        "GET", f"{GH_BASE}/rate_limit"),
    ("gh_meta",              "GET", f"{GH_BASE}/meta"),
    ("gh_gitignore",         "GET", f"{GH_BASE}/gitignore/templates"),
    ("gh_licenses",          "GET", f"{GH_BASE}/licenses"),
    ("gh_events",            "GET", f"{GH_BASE}/events?per_page=100"),
    ("gh_zen",               "GET", f"{GH_BASE}/zen"),
    ("gh_octocat",           "GET", f"{GH_BASE}/octocat"),
    ("gh_search_uap",        "GET", f"{GH_BASE}/search/repositories?q=UAP+anomaly+detection&sort=updated&per_page=30"),
    ("gh_search_skinwalker", "GET", f"{GH_BASE}/search/repositories?q=skinwalker+ranch&sort=updated&per_page=30"),
    ("gh_search_aawsap",     "GET", f"{GH_BASE}/search/repositories?q=AAWSAP+AATIP&sort=updated&per_page=30"),
    ("gh_search_plasma",     "GET", f"{GH_BASE}/search/repositories?q=plasma+physics+UAP&sort=updated&per_page=30"),
]

# ── ROUTE FETCHER (autohook wrapped) ────────────────────────────────────────
@autohook(max_retries=5)
def fetch_route(name: str, method: str, url: str, headers: dict = None, data: dict = None, timeout: float = 30.0) -> dict:
    """Fetch a single route with autohook recovery."""
    t0 = time.perf_counter()
    h = dict(headers) if headers else {}
    try:
        if method == "GET":
            resp = _session.get(url, headers=h, timeout=timeout)
        else:
            resp = _session.post(url, headers=h, json=data, timeout=timeout)
        resp.raise_for_status()
        latency = (time.perf_counter() - t0) * 1000
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        return {
            "name": name,
            "status": resp.status_code,
            "latency_ms": round(latency, 2),
            "body": body,
            "headers": dict(resp.headers),
            "url": url,
        }
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return {
            "name": name,
            "status": getattr(getattr(e, "response", None), "status_code", 0),
            "latency_ms": round(latency, 2),
            "error": str(e),
            "url": url,
        }

# ── PARALLEL RACE ALL ROUTES ────────────────────────────────────────────────
def race_all_github_routes(max_workers: int = 16) -> List[dict]:
    """Race all GitHub routes in parallel. No rollback. Fix errors inline."""
    tasks = []
    for name, method, url in GH_ROUTES:
        tasks.append((fetch_route, (name, method, url, GH_HEADERS), {}))
    return autohook_race(tasks, max_workers=max_workers)

# ── SAVE RESULTS PERMANENT ──────────────────────────────────────────────────
def save_results(results: List[dict], prefix: str = "github_recon") -> Tuple[Path, Optional[Path]]:
    """Save results to JSON and Parquet permanently."""
    ts = int(time.time())
    json_path = RECON_DIR / f"{prefix}_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    try:
        import pandas as pd
        import pyarrow.parquet as pq
        import pyarrow as pa
        rows = []
        for r in results:
            if isinstance(r, dict) and not r.get("_autohook_error"):
                rows.append({
                    "name": r.get("name", ""),
                    "status": r.get("status", 0),
                    "latency_ms": r.get("latency_ms", 0),
                    "url": r.get("url", ""),
                    "error": r.get("error", ""),
                    "body_preview": str(r.get("body", ""))[:500],
                })
            elif isinstance(r, dict):
                rows.append({
                    "name": r.get("_func", "unknown"),
                    "status": -1,
                    "latency_ms": 0,
                    "url": "",
                    "error": r.get("_exception", ""),
                    "body_preview": "",
                })
        if rows:
            df = pd.DataFrame(rows)
            parquet_path = PARQUET_DIR / f"{prefix}_{ts}.parquet"
            table = pa.Table.from_pandas(df)
            pq.write_table(table, str(parquet_path))
            return json_path, parquet_path
    except Exception as e:
        pass
    return json_path, None

# ── DRIVE9 OPS ──────────────────────────────────────────────────────────────
@autohook(max_retries=3)
def drive9_probe() -> dict:
    """Probe drive9 binary for available commands."""
    import subprocess
    result = subprocess.run(["drive9", "--help"], capture_output=True, text=True, timeout=10)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "rc": result.returncode,
    }

@autohook(max_retries=3)
def drive9_ctx_show() -> dict:
    """Show current drive9 context."""
    import subprocess
    result = subprocess.run(["drive9", "ctx", "show", "--json"], capture_output=True, text=True, timeout=10)
    try:
        return json.loads(result.stdout)
    except:
        return {"stdout": result.stdout, "stderr": result.stderr, "rc": result.returncode}

# ── AGENT GW TEST ───────────────────────────────────────────────────────────
@autohook(max_retries=3)
def test_agent_gw() -> dict:
    """Test AgentGwClient import and basic functionality."""
    try:
        client = AgentGwClient()
        return {
            "import_ok": True,
            "version": getattr(sys.modules.get("agent_gw_client"), "__version__", "unknown"),
            "base_url": client.base_url,
            "timeout": client.timeout,
        }
    except Exception as e:
        return {"import_ok": False, "error": str(e)}

# ── MAIN RECON ──────────────────────────────────────────────────────────────
def main_recon():
    print("=" * 70)
    print("RECON_LOADERS — Parallel Async GitHub + Drive9 + AgentGW Recon")
    print("=" * 70)
    
    # Phase 1: Load parquet intel
    print("\n[PHASE 1] Loading all parquet intel...")
    intel = load_all_parquet()
    if isinstance(intel, dict) and intel.get("_autohook_error"):
        print(f"    ⚠ Parquet load failed: {intel.get('_exception')}")
    else:
        print(f"    ✓ Loaded {len(intel)} parquet datasets")
        for name, data in intel.items():
            if isinstance(data, dict) and "rows" in data:
                print(f"      {name}: {data['rows']} rows, {len(data['cols'])} cols")
    
    # Phase 2: Race all GitHub routes
    print("\n[PHASE 2] Racing all GitHub API routes in parallel...")
    t0 = time.perf_counter()
    results = race_all_github_routes(max_workers=16)
    total_ms = (time.perf_counter() - t0) * 1000
    print(f"    ✓ All {len(GH_ROUTES)} routes completed in {total_ms:.1f}ms")
    
    ok = [r for r in results if isinstance(r, dict) and r.get("status", 0) in [200, 201, 204]]
    fail = [r for r in results if isinstance(r, dict) and r.get("status", 0) not in [200, 201, 204]]
    print(f"    ✓ OK: {len(ok)}  |  ✗ FAIL: {len(fail)}")
    
    # Phase 3: Save permanent
    print("\n[PHASE 3] Saving results permanently...")
    json_path, parquet_path = save_results(results, "github_recon")
    print(f"    ✓ JSON:  {json_path}")
    if parquet_path:
        print(f"    ✓ Parquet: {parquet_path}")
    
    # Phase 4: Drive9 probe
    print("\n[PHASE 4] Probing drive9...")
    d9_help = drive9_probe()
    if not d9_help.get("_autohook_error"):
        print(f"    ✓ drive9 --help: rc={d9_help.get('rc')}")
    d9_ctx = drive9_ctx_show()
    if d9_ctx and not d9_ctx.get("_autohook_error"):
        print(f"    ✓ drive9 ctx: {str(d9_ctx)[:200]}")
    
    # Phase 5: AgentGW test
    print("\n[PHASE 5] Testing AgentGwClient...")
    gw = test_agent_gw()
    if gw and not gw.get("_autohook_error"):
        print(f"    ✓ AgentGW: import_ok={gw.get('import_ok')}, base_url={gw.get('base_url')}")
    
    print("\n" + "=" * 70)
    print("RECON COMPLETE — All data saved permanent")
    print("=" * 70)
    return results

if __name__ == "__main__":
    main_recon()
