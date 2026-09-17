#!/usr/bin/env python3
"""session_bootstrap_v1.py — Self-healing session bootstrap.
Run at start of every new session. Recreates missing autohooks, loads them, reminds about magic.
"""
import os, sys, subprocess, json, time, pathlib

OUT = pathlib.Path("/mnt/agents/output")
AUTOHOOK_PATH = OUT / "autohook_v7.py"
BOOTSTRAP_STATE = OUT / ".bg_state" / "bootstrap.json"

# Embedded autohook template for self-healing
AUTOHOOK_TEMPLATE = """#!/usr/bin/env python3
import os, sys, subprocess, json, time, threading, traceback, pathlib

OUT = pathlib.Path("/mnt/agents/output")
LOG = OUT / ".bg_logs" / "ah7.log"
TOOL_LOG = OUT / ".bg_logs" / "ah7_tools.jsonl"
STATE = OUT / ".bg_state" / "ah7_state.json"
CHUNK_DIR = OUT / ".moonbox_chunks"
for d in (LOG.parent, TOOL_LOG.parent, STATE.parent, CHUNK_DIR):
    d.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
_state = {"calls": 0, "start": time.time(), "last_reset": 0}

def lg(msg, lvl="INFO"):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] [{lvl}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except:
        pass

def mitm_log(tool_type, cmd, rc, out, err, dt_ms):
    try:
        entry = {
            "ts": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "tool": tool_type,
            "cmd": str(cmd)[:2000],
            "rc": rc,
            "out_len": len(out) if out else 0,
            "err_len": len(err) if err else 0,
            "dt_ms": dt_ms,
            "pid": os.getpid(),
        }
        with _lock:
            with open(TOOL_LOG, 'a') as f:
                f.write(json.dumps(entry) + '\n')
    except:
        pass

_orig_run = subprocess.run
_orig_popen = subprocess.Popen

def _run(*a, **kw):
    t0 = time.time()
    try:
        r = _orig_run(*a, **kw)
    except Exception as e:
        mitm_log("run_ERR", a[0] if a else kw.get('args',''), -1, "", str(e), int((time.time()-t0)*1000))
        raise
    dt = int((time.time()-t0)*1000)
    cmd = a[0] if a else kw.get('args','')
    mitm_log("run", cmd, r.returncode, r.stdout[:8000] if r.stdout else "", r.stderr[:2000] if r.stderr else "", dt)
    return r

def _popen(*a, **kw):
    mitm_log("popen", a[0] if a else kw.get('args',''), 0, "", "", 0)
    return _orig_popen(*a, **kw)

subprocess.run = _run
subprocess.Popen = _popen

def chunk_save(data, prefix="chunk"):
    if isinstance(data, bytes):
        data = data.decode('utf-8', errors='replace')
    sz = 9000
    files = []
    for i in range(0, len(data), sz):
        part = data[i:i+sz]
        fn = CHUNK_DIR / f"{prefix}_{int(time.time())}_{i:05d}.txt"
        fn.write_text(part)
        files.append(str(fn))
    return files

def run(cmd, t=15, cwd=None):
    lg(f"RUN: {cmd[:120]}")
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t, cwd=cwd)
        if r.stdout and len(r.stdout) > 9500:
            files = chunk_save(r.stdout, "stdout")
            lg(f"CHUNKED stdout -> {len(files)} files")
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        lg(f"TIMEOUT: {cmd[:120]}", "WARN")
        return False, "", "TIMEOUT"
    except Exception as e:
        lg(f"EXC: {e}", "ERROR")
        return False, "", str(e)
"""

def bootstrap():
    results = {"ts": time.time(), "actions": [], "magic": {}}

    for d in [OUT / ".bg_logs", OUT / ".bg_state", OUT / ".moonbox_chunks"]:
        d.mkdir(parents=True, exist_ok=True)

    if not AUTOHOOK_PATH.exists():
        AUTOHOOK_PATH.write_text(AUTOHOOK_TEMPLATE)
        AUTOHOOK_PATH.chmod(0o755)
        results["actions"].append("RECREATED autohook_v7.py")
    else:
        results["actions"].append("FOUND autohook_v7.py")

    # Load autohook via import, not exec
    sys.path.insert(0, str(OUT))
    try:
        import autohook_v7
        results["actions"].append("IMPORTED autohook_v7")
    except Exception as e:
        results["actions"].append(f"IMPORT_FAIL: {e}")

    results["magic"] = {
        "!": "shell escape in IPython",
        "%": "line magic",
        "%%": "cell magic",
        "note": "Always available in IPython. Use ! for shell, %%bash for blocks.",
    }

    BOOTSTRAP_STATE.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_STATE.write_text(json.dumps(results, indent=2, default=str))
    return results

if __name__ == "__main__":
    r = bootstrap()
    print(json.dumps(r, indent=2, default=str))
    print("\n=== BOOTSTRAP COMPLETE ===")
