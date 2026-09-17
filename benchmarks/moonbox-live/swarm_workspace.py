#!/usr/bin/env python3
"""swarm_workspace.py - Parallel task execution with dynamic workers."""
import os, concurrent.futures, time, json, pathlib, psutil

class Swarm:
    def __init__(self, max_workers=None):
        mem = psutil.virtual_memory()
        cpu = os.cpu_count() or 4
        self.workers = max_workers or min(cpu * 2, max(4, mem.available // (100 * 1024 * 1024)))
        self.results = []
        self.t0 = time.time()

    def map(self, fn, items):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.workers) as ex:
            self.results = list(ex.map(fn, items))
        dt = (time.time() - self.t0) * 1000
        return {"results": self.results, "elapsed_ms": round(dt, 2), "workers": self.workers}

    def filter_ok(self):
        return [r for r in self.results if isinstance(r, dict) and r.get("ok", False)]

    def filter_fail(self):
        return [r for r in self.results if isinstance(r, dict) and not r.get("ok", False)]
