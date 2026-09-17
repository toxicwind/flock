#!/usr/bin/env python3
"""
hook_master.py - Master interception hook for all tool calls.
Replaces auto_hook.py with full trace, decode, and persistence.
No tmp/ usage. Everything goes to /mnt/agents/output/.bg_logs/
"""
import os, sys, json, time, hashlib, inspect, threading, traceback
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("/mnt/agents/output/.bg_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

SEED_FILE = Path("/mnt/agents/output/.bg_logs/session_seed.jsonl")
TRACE_FILE = Path("/mnt/agents/output/.bg_logs/master_trace.jsonl")

class ToolHook:
    def __init__(self):
        self.session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        self.call_count = 0
        self.lock = threading.Lock()
        self._write_seed()

    def _write_seed(self):
        seed = {
            "ts": datetime.now().isoformat(),
            "session_id": self.session_id,
            "pid": os.getpid(),
            "uid": os.getuid(),
            "euid": os.geteuid(),
            "gid": os.getgid(),
            "cwd": os.getcwd(),
            "python": sys.version,
            "argv": sys.argv,
        }
        with open(SEED_FILE, "a") as f:
            f.write(json.dumps(seed, default=str) + "\n")

    def log_call(self, tool_name, args, kwargs, result, error=None):
        with self.lock:
            self.call_count += 1
            entry = {
                "ts": datetime.now().isoformat(),
                "session_id": self.session_id,
                "seq": self.call_count,
                "tool": tool_name,
                "args_hash": hashlib.sha256(str(args).encode()).hexdigest()[:16],
                "kwargs_hash": hashlib.sha256(str(kwargs).encode()).hexdigest()[:16],
                "result_type": type(result).__name__ if result else None,
                "error": str(error) if error else None,
                "stack": traceback.format_stack(limit=3)[:-1] if error else None,
            }
            with open(TRACE_FILE, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
            return result

    def wrap(self, func, name):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                self.log_call(name, args, kwargs, result)
                return result
            except Exception as e:
                self.log_call(name, args, kwargs, None, error=e)
                raise
        return wrapper

HOOK = ToolHook()

if __name__ == "__main__":
    print(f"hook_master initialized: {HOOK.session_id}")
    print(f"log dir: {LOG_DIR}")
    print(f"seed file: {SEED_FILE}")
    print(f"trace file: {TRACE_FILE}")
