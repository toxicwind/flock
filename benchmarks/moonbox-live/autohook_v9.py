#!/usr/bin/env python3
"""autohook_v9.py - Working session bootstrap. NO subprocess patch."""
import os, sys, subprocess, json, time, pathlib, threading

OUT = pathlib.Path("/mnt/agents/output")
LOG = OUT / ".bg_logs" / "ah9.log"
CHUNK_DIR = OUT / ".moonbox_chunks"
for d in (LOG.parent, CHUNK_DIR):
    d.mkdir(parents=True, exist_ok=True)

_log_lock = threading.Lock()

def lg(msg, lvl="INFO"):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] [{lvl}] {msg}"
    print(line, flush=True)
    try:
        with _log_lock:
            with open(LOG, 'a') as f:
                f.write(line + '\n')
    except:
        pass

def chunk_save(data, prefix="chunk"):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    if len(data) <= 9000:
        return []
    files = []
    for i in range(0, len(data), 9000):
        part = data[i:i+9000]
        fn = CHUNK_DIR / f"{prefix}_{int(time.time())}_{i:05d}.txt"
        fn.write_text(part)
        files.append(str(fn))
    return files

def frun(cmd, t=15, cwd=None):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, cwd=cwd)
        dt = (time.time() - t0) * 1000
        if r.stdout and len(r.stdout) > 9500:
            files = chunk_save(r.stdout, "stdout")
            lg(f"CHUNKED {len(files)} files for: {cmd[:80]}")
        lg(f"RUN {dt:.1f}ms rc={r.returncode}: {cmd[:80]}")
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        lg(f"TIMEOUT: {cmd[:80]}", "WARN")
        return False, "", "TIMEOUT"
    except Exception as e:
        lg(f"EXC: {e}", "ERROR")
        return False, "", str(e)

def gcommit(path, msg="auto"):
    if not pathlib.Path(path).is_dir():
        return False
    lock = os.path.join(path, '.git', 'index.lock')
    if os.path.exists(lock):
        try:
            os.remove(lock)
        except:
            pass
    frun(f"cd {path} && git add -A", t=8)
    ok, out, err = frun(f'cd {path} && git commit -m "{msg}"', t=8)
    return ok or 'nothing to commit' in (err + out).lower()

lg("§AUTOHOOK_V9_LOADED§")
