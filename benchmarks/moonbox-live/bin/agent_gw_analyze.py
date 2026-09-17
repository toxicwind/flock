#!/usr/bin/env python3
"""
agent_gw_analyze.py - Analyze the agent-gateway binary from reverse-kimi-envd-fixed.
Deep ELF inspection, string extraction, Go symbol recovery.
"""
import os, json, subprocess, struct
from pathlib import Path
from datetime import datetime

OUT = Path("/mnt/agents/output/.bg_logs/agent_gw_analysis.jsonl")
OUT.parent.mkdir(parents=True, exist_ok=True)

# Find the binary
SEARCH_PATHS = [
    "/mnt/agents/output/private_repos/reverse-kimi-envd-fixed",
    "/mnt/agents/output/kimi-consolidated/envd",
    "/mnt/agents/output/.backup",
    "/mnt/agents/output/bin",
]

def find_binaries():
    bins = []
    for base in SEARCH_PATHS:
        base = Path(base)
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_file() and not f.is_symlink():
                try:
                    with open(f, "rb") as fh:
                        magic = fh.read(4)
                        if magic == b"\x7fELF":
                            bins.append(str(f))
                except:
                    pass
    return bins

def analyze_elf(path):
    result = {"path": path, "ts": datetime.now().isoformat()}

    # readelf -h
    try:
        out = subprocess.run(["readelf", "-h", path], capture_output=True, text=True, timeout=10)
        result["readelf_h"] = out.stdout[:2000]
    except:
        result["readelf_h"] = "failed"

    # readelf -S
    try:
        out = subprocess.run(["readelf", "-S", path], capture_output=True, text=True, timeout=10)
        result["readelf_S"] = out.stdout[:2000]
    except:
        result["readelf_S"] = "failed"

    # strings
    try:
        out = subprocess.run(["strings", "-n", "8", path], capture_output=True, text=True, timeout=15)
        lines = out.stdout.split("\n")
        # Filter for interesting strings
        interesting = [l for l in lines if any(x in l.lower() for x in [
            "kimi", "agent", "gateway", "sandbox", "api", "grpc", "websocket",
            "token", "auth", "session", "context", "model", "moonshot",
            "envd", "drive9", "portal", "kernel", "msh", "cdn"
        ])]
        result["strings_interesting"] = interesting[:200]
        result["strings_total"] = len(lines)
    except:
        result["strings_interesting"] = []
        result["strings_total"] = 0

    # file command
    try:
        out = subprocess.run(["file", path], capture_output=True, text=True, timeout=5)
        result["file_type"] = out.stdout.strip()
    except:
        result["file_type"] = "unknown"

    # Check for Go build info
    try:
        out = subprocess.run(["strings", "-n", "20", path], capture_output=True, text=True, timeout=10)
        go_info = [l for l in out.stdout.split("\n") if "go.build" in l or "path\t" in l or "mod\t" in l]
        result["go_buildinfo"] = go_info[:50]
    except:
        result["go_buildinfo"] = []

    return result

def main():
    bins = find_binaries()
    print(f"Found {len(bins)} ELF binaries")

    for b in bins:
        print(f"Analyzing: {b}")
        result = analyze_elf(b)
        with open(OUT, "a") as f:
            f.write(json.dumps(result) + "\n")
        print(f"  type: {result.get('file_type', '?')}")
        print(f"  strings: {result.get('strings_total', 0)} total, {len(result.get('strings_interesting', []))} interesting")

if __name__ == "__main__":
    main()
