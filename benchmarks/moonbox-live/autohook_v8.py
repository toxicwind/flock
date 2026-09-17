#!/usr/bin/env python3
"""autohook_v8 - clean session bootstrap."""
import os, sys, subprocess, json, time, pathlib, threading

OUT = pathlib.Path("/mnt/agents/output")

def lg(msg, lvl="INFO"):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] [{lvl}] {msg}"
    print(line, flush=True)
    try:
        with open(OUT / ".bg_logs" / "ah8.log", 'a') as f:
            f.write(line + '\n')
    except:
        pass

lg("§AUTOHOOK_V8_LOADED§")

# Chunk helper
def chunk_save(data, prefix="chunk"):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    CHUNK_DIR = OUT / ".moonbox_chunks"
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for i in range(0, len(data), 9000):
        part = data[i:i+9000]
        fn = CHUNK_DIR / f"{prefix}_{int(time.time())}_{i:05d}.txt"
        fn.write_text(part)
        files.append(str(fn))
    return files

# Fast run
def frun(cmd, t=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        if r.stdout and len(r.stdout) > 9500:
            chunk_save(r.stdout, "stdout")
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except Exception as e:
        return False, "", str(e)

lg("§AUTOHOOK_V8_READY§")
