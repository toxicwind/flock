#!/usr/bin/env python3
"""github_ops — GitHub submodule and repo operations with autohook recovery.

Imports autohook.py and recon_loaders.py maximally. No repeated code.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(_script_dir))
from autohook import autohook, Autohook
from recon_loaders import GH_HEADERS, GH_BASE, _session

# ── SUBMODULE OPS ───────────────────────────────────────────────────────────
@autohook(max_retries=3)
def add_submodule(repo_dir: Path, submodule_url: str, path: str) -> dict:
    """Add a Git submodule. Uses root wrapper if needed."""
    cmd = ["git", "-C", str(repo_dir), "submodule", "add", "--force", submodule_url, path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {
        "cmd": " ".join(cmd),
        "rc": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

@autohook(max_retries=3)
def update_submodules(repo_dir: Path, init: bool = True) -> dict:
    """Update all submodules."""
    cmd = ["git", "-C", str(repo_dir), "submodule", "update", "--init", "--recursive"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return {
        "cmd": " ".join(cmd),
        "rc": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

@autohook(max_retries=3)
def sync_submodules(repo_dir: Path) -> dict:
    """Sync submodules."""
    cmd = ["git", "-C", str(repo_dir), "submodule", "sync", "--recursive"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return {
        "cmd": " ".join(cmd),
        "rc": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

# ── GITHUB API OPS ──────────────────────────────────────────────────────────
@autohook(max_retries=3)
def get_repo_info(owner: str, repo: str) -> dict:
    """Get repo info from GitHub API."""
    resp = _session.get(f"{GH_BASE}/repos/{owner}/{repo}", headers=GH_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

@autohook(max_retries=3)
def list_user_repos() -> List[dict]:
    """List all repos for authenticated user."""
    repos = []
    page = 1
    while True:
        resp = _session.get(f"{GH_BASE}/user/repos?per_page=100&page={page}", headers=GH_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

@autohook(max_retries=3)
def search_repos(query: str, per_page: int = 30) -> dict:
    """Search GitHub repos."""
    resp = _session.get(f"{GH_BASE}/search/repositories?q={query}&sort=updated&per_page={per_page}", headers=GH_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()

# ── TARGET REPOS FOR SUBMODULES (UAP-related) ───────────────────────────────
UAP_SUBMODULES = [
    ("https://github.com/HawkFranklin-Research/UAP-Files.git", "intel/uap-files"),
    ("https://github.com/AdvancedScientificResearchProjects/UAP_Reverse_Engineering_Study.git", "intel/uap-reverse-engineering"),
    ("https://github.com/zexiro/uap-disclosure-archive.git", "intel/uap-disclosure-archive"),
    ("https://github.com/15-minute-discourse/gov-ufo-investigations.git", "intel/gov-ufo-investigations"),
]

# ── MAIN OPS ────────────────────────────────────────────────────────────────
def add_all_uap_submodules(target_repo: Path) -> List[dict]:
    """Add all UAP-related submodules to target repo."""
    results = []
    for url, path in UAP_SUBMODULES:
        print(f"    Adding submodule: {path}")
        result = add_submodule(target_repo, url, path)
        results.append(result)
        if result.get("rc") == 0:
            print(f"      ✓ Success")
        else:
            print(f"      ✗ Failed: {result.get('stderr', '')[:200]}")
    # Update all
    print("    Updating submodules...")
    update_result = update_submodules(target_repo)
    results.append(update_result)
    return results

if __name__ == "__main__":
    print("github_ops — Submodule and repo operations")
