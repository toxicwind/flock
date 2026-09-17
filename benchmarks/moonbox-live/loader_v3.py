#!/usr/bin/env python3
"""loader_v3 — unified fast loader. Imports all hooks, probes, shims. One file."""
import os, sys, subprocess, json, time, pathlib, threading, traceback

OUT = pathlib.Path("/mnt/agents/output")

def lg(msg):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)

def run(cmd, t=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return r.returncode == 0, r.stdout or "", r.stderr or ""
    except Exception as e:
        return False, "", str(e)

class Loader:
    def __init__(self):
        self.hooks = []
        self.state = {"boot": time.time(), "calls": 0}

    def boot(self):
        lg("LOADERv3_BOOT")
        self.patch_subprocess()
        self.load_autohook()
        self.load_envd_shim()
        self.probe_all()
        lg("LOADERv3_READY")

    def patch_subprocess(self):
        _orig = subprocess.run
        def _run(*a, **kw):
            self.state["calls"] += 1
            return _orig(*a, **kw)
        subprocess.run = _run
        lg("PATCH: subprocess.run")

    def load_autohook(self):
        ah = OUT / "autohook_v7.py"
        if ah.exists():
            try:
                exec(compile(ah.read_text(), str(ah), 'exec'), {"__name__":"__autohook__"})
                lg("LOAD: autohook_v7")
                self.hooks.append("autohook_v7")
            except Exception as e:
                lg(f"LOAD_FAIL autohook_v7: {e}")

    def load_envd_shim(self):
        sh = OUT / "envd_shim_v4.py"
        if sh.exists():
            lg(f"FOUND: envd_shim_v4.py (run separately: python3 {sh})")

    def probe_all(self):
        lg("PROBE_START")
        ok, out, _ = run("python3 /mnt/agents/output/portal_probe_v2.py", t=15)
        if ok:
            try:
                data = json.loads(out)
                lg(f"PROBE_OK: {len(data)} keys")
                # Save merged state
                (OUT / ".bg_state" / "loader_probe.json").write_text(json.dumps(data, indent=2, default=str))
            except:
                lg("PROBE_PARSE_FAIL")
        else:
            lg("PROBE_FAIL")

    def status(self):
        return self.state

if __name__ == "__main__":
    L = Loader()
    L.boot()
    print(json.dumps(L.status(), indent=2))
