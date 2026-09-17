#!/usr/bin/env python3
"""
persist_tracker.py - Auto-updating parquet tracker for all project state.
No tmp/. Everything persists to /mnt/agents/output/.bg_logs/
"""
import os, json, sys, hashlib
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("pandas not available, using JSON fallback")

BASE = Path("/mnt/agents/output")
LOG_DIR = BASE / ".bg_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
PARQUET_PATH = LOG_DIR / "project_state.parquet"
JSON_PATH = LOG_DIR / "project_state.jsonl"

def scan_projects():
    records = []
    for item in BASE.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue
        if item.name in (".bg_logs", "bin"):
            continue

        file_count = 0
        total_size = 0
        py_count = 0
        js_count = 0
        md_count = 0
        ipynb_count = 0
        hidden_count = 0
        git_present = False

        for root, dirs, files in os.walk(item):
            if ".git" in dirs:
                git_present = True
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".next", "__pycache__", ".venv")]
            for f in files:
                fpath = Path(root) / f
                try:
                    st = fpath.stat()
                    size = st.st_size
                    total_size += size
                    file_count += 1
                    if f.endswith(".py"):
                        py_count += 1
                    elif f.endswith(".js") or f.endswith(".ts"):
                        js_count += 1
                    elif f.endswith(".md"):
                        md_count += 1
                    elif f.endswith(".ipynb"):
                        ipynb_count += 1
                    if f.startswith("."):
                        hidden_count += 1
                except:
                    pass

        records.append({
            "ts": datetime.now().isoformat(),
            "project": item.name,
            "path": str(item),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "py_count": py_count,
            "js_count": js_count,
            "md_count": md_count,
            "ipynb_count": ipynb_count,
            "hidden_count": hidden_count,
            "has_git": git_present,
        })
    return records

def save(records):
    if HAS_PANDAS:
        df = pd.DataFrame(records)
        if PARQUET_PATH.exists():
            old = pd.read_parquet(PARQUET_PATH)
            df = pd.concat([old, df], ignore_index=True)
        df.to_parquet(PARQUET_PATH, index=False)
        print(f"Parquet saved: {PARQUET_PATH} ({len(df)} total rows)")
    else:
        with open(JSON_PATH, "a") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        print(f"JSONL saved: {JSON_PATH}")

def main():
    records = scan_projects()
    save(records)
    for r in records:
        print(f"  {r['project']}: {r['file_count']} files, {r['total_size_bytes']:,} bytes, git={r['has_git']}")

if __name__ == "__main__":
    main()
