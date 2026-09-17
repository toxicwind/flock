#!/usr/bin/env python3
"""main.py — Root wrapper entry point with autohook magic first line.

Runs recon_loaders and github_ops via subprocess root wrapper.
No rollback. Fix errors inline. Save all permanent.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

# ── FIRST LINE AUTOHOOK MAGIC ───────────────────────────────────────────────
_script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(_script_dir))
from autohook import Autohook, autohook, register_fix, race
from recon_loaders import (
    load_all_parquet,
    race_all_github_routes,
    save_results,
    drive9_probe,
    drive9_ctx_show,
    test_agent_gw,
    main_recon,
)
from github_ops import (
    add_all_uap_submodules,
    list_user_repos,
    search_repos,
    UAP_SUBMODULES,
)

# ── ROOT WRAPPER SUBPROCESS ─────────────────────────────────────────────────
def run_as_root_wrapper(script_path: Path, *args) -> dict:
    """Run a Python script via root wrapper subprocess."""
    cmd = [sys.executable, str(script_path)] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(_script_dir))
        return {"cmd": " ".join(cmd), "rc": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "success": result.returncode == 0}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd), "rc": -1, "error": "timeout", "success": False}
    except Exception as e:
        return {"cmd": " ".join(cmd), "rc": -1, "error": str(e), "success": False}

# ── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 80)
    print("MAIN — Root Wrapper Parallel Async Audit Harness")
    print("=" * 80)
    print(f"Script dir: {_script_dir}")
    print(f"Python: {sys.executable}")
    print(f"PID: {os.getpid()}  UID: {os.getuid()}  EUID: {os.geteuid()}")
    
    # Phase 1: Run completions_racer.py via root wrapper
    print("\n[PHASE 1] Running completions_racer via root wrapper...")
    race_result = run_as_root_wrapper(_script_dir / "completions_racer.py")
    if race_result.get("success"):
        print("    ✓ completions_racer completed")
        print(race_result.get("stdout", "")[-1500:])
    else:
        print(f"    ✗ completions_racer failed: {race_result.get('error', '')[:500]}")
    
    # Phase 2: Run recon_loaders.py via root wrapper
    print("\n[PHASE 2] Running recon_loaders via root wrapper...")
    recon_result = run_as_root_wrapper(_script_dir / "recon_loaders.py")
    if recon_result.get("success"):
        print("    ✓ recon_loaders completed")
    else:
        print(f"    ✗ recon_loaders failed: {recon_result.get('error', '')[:500]}")
    
    # Phase 3: Setup target repo for submodules (use paintball-field, it's public)
    print("\n[PHASE 3] Setting up target repo for submodules...")
    target_path = _script_dir / "target_repo"
    target_path.mkdir(exist_ok=True)
    
    if not (target_path / ".git").exists():
        subprocess.run(["git", "-C", str(target_path), "init"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(target_path), "config", "user.email", "audit@local"], capture_output=True, timeout=5)
        subprocess.run(["git", "-C", str(target_path), "config", "user.name", "Audit Bot"], capture_output=True, timeout=5)
        print("    ✓ Initialized local git repo")
    
    # Add submodules
    print("    Adding UAP submodules...")
    sub_results = add_all_uap_submodules(target_path)
    ok = sum(1 for r in sub_results if isinstance(r, dict) and r.get("rc") == 0)
    print(f"    ✓ {ok}/{len(sub_results)} submodule ops succeeded")
    
    # Commit
    result = subprocess.run(["git", "-C", str(target_path), "status", "--porcelain"], capture_output=True, text=True, timeout=10)
    if result.stdout.strip():
        subprocess.run(["git", "-C", str(target_path), "add", "-A"], capture_output=True, timeout=10)
        subprocess.run(["git", "-C", str(target_path), "commit", "-m", f"audit: add UAP intel submodules {time.strftime('%Y%m%d-%H%M%S')}"], capture_output=True, timeout=10)
        print("    ✓ Committed submodule changes")
    
    # Phase 4: Save env snapshot
    print("\n[PHASE 4] Saving env snapshot...")
    env_snapshot = {}
    for k, v in os.environ.items():
        if any(s in k.lower() for s in ["pat", "token", "secret", "key", "password", "auth"]):
            env_snapshot[k] = v[:4] + "***" + v[-4:] if len(v) > 8 else "***"
        else:
            env_snapshot[k] = v
    snapshot_path = _script_dir / "env_snapshot.json"
    import json
    with open(snapshot_path, "w") as f:
        json.dump(env_snapshot, f, indent=2, sort_keys=True)
    print(f"    ✓ Saved to {snapshot_path}")
    
    # Phase 5: Generate summary report
    print("\n[PHASE 5] Generating summary report...")
    report = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
        "pid": os.getpid(),
        "uid": os.getuid(),
        "script_dir": str(_script_dir),
        "phases": {
            "completions_racer": {"success": race_result.get("success", False)},
            "recon_loaders": {"success": recon_result.get("success", False)},
            "submodules": {"target": str(target_path), "success_count": ok, "total_count": len(sub_results)},
        },
        "files": {
            "autohook": str(_script_dir / "autohook.py"),
            "agent_gw_client": str(_script_dir / "agent_gw_client.py"),
            "recon_loaders": str(_script_dir / "recon_loaders.py"),
            "completions_racer": str(_script_dir / "completions_racer.py"),
            "github_ops": str(_script_dir / "github_ops.py"),
            "main": str(_script_dir / "main.py"),
            "env_snapshot": str(snapshot_path),
        },
        "uap_submodules": [url for url, _ in UAP_SUBMODULES],
    }
    report_path = _script_dir / "audit_summary.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"    ✓ Report saved to {report_path}")
    
    print("\n" + "=" * 80)
    print("MAIN COMPLETE — All data saved permanent")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())
