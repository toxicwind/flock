
#!/usr/bin/env python3
"""
RaceGlass v3.14 — Asyncio Race Scaffold with 28s Hard Kill
Full unshare schema, in-memory parquet, kernel-level probing
"""
import asyncio
import subprocess
import sys
import os
import json
import time
import signal
import tempfile
import pathlib
import struct
import socket
import fcntl
import array
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# Try pyarrow — if not available, use JSON fallback
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False
    print("[RACE] WARNING: pyarrow not available, using JSON fallback")

RACE_TIMEOUT = 28.0
MAX_RACE_PROBES = 8

@dataclass
class RaceResult:
    probe_id: str
    tier: int
    cmd: str
    start_ts: float
    end_ts: float
    duration_ms: float
    exit_code: Optional[int]
    stdout: str
    stderr: str
    killed: bool
    wha_moment: Optional[str]
    metadata: Dict[str, Any]

class RaceGlass:
    def __init__(self, max_probes: int = MAX_RACE_PROBES, timeout: float = RACE_TIMEOUT):
        self.max_probes = max_probes
        self.timeout = timeout
        self.results: List[RaceResult] = []
        self.wha_log: List[str] = []
        self._lock = asyncio.Lock()

    def wha(self, msg: str, data: Any = None):
        """Reactive "whoa what is this" logger"""
        entry = f"[WHΑ {datetime.utcnow().isoformat()}] {msg}"
        if data:
            entry += f" | data={json.dumps(data, default=str)[:500]}"
        self.wha_log.append(entry)
        print(entry, file=sys.stderr)

    async def _run_single(self, probe_id: str, tier: int, cmd: str, 
                          env: Optional[Dict] = None,
                          cwd: Optional[str] = None,
                          use_unshare: bool = False) -> RaceResult:
        """Run a single probe with 28s hard kill"""
        start = time.time()

        # Build command with unshare if requested
        if use_unshare and os.path.exists("/usr/bin/unshare"):
            full_cmd = ["unshare", "-U", "-r", "bash", "-c", cmd]
        else:
            full_cmd = ["bash", "-c", cmd]

        self.wha(f"PROBE_START {probe_id} tier={tier} cmd={cmd[:80]}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})},
                cwd=cwd,
                preexec_fn=os.setsid  # Create new process group for clean kill
            )

            # 28s hard kill timer
            async def killer():
                await asyncio.sleep(self.timeout)
                if proc.returncode is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        self.wha(f"KILL28_FIRED {probe_id} pid={proc.pid}")
                    except ProcessLookupError:
                        pass

            killer_task = asyncio.create_task(killer())

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout + 2
                )
                killed = False
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = b"", b"RACE_TIMEOUT_EXCEEDED"
                killed = True

            killer_task.cancel()
            try:
                await killer_task
            except asyncio.CancelledError:
                pass

        except Exception as e:
            stdout, stderr = b"", f"RACE_EXCEPTION: {e}".encode()
            killed = True
            proc = type("FakeProc", (), {"returncode": -1})()

        end = time.time()
        duration_ms = (end - start) * 1000

        # Detect "whoa" moments in output
        wha = None
        out_str = stdout.decode("utf-8", errors="replace")[:10000]
        err_str = stderr.decode("utf-8", errors="replace")[:10000]

        wha_triggers = ["password", "token", "secret", "key=", "ssh", "portal", 
                        "capability", "moonbox", "envd", "drive9", "overlay", 
                        "blk-cube", "prod", "capability", "admin", "root"]
        combined = (out_str + err_str).lower()
        for trigger in wha_triggers:
            if trigger in combined:
                wha = f"TRIGGER:{trigger}"
                self.wha(f"WHΑ_MOMENT {probe_id} trigger={trigger}")
                break

        result = RaceResult(
            probe_id=probe_id,
            tier=tier,
            cmd=cmd,
            start_ts=start,
            end_ts=end,
            duration_ms=duration_ms,
            exit_code=proc.returncode,
            stdout=out_str,
            stderr=err_str,
            killed=killed,
            wha_moment=wha,
            metadata={"pid": getattr(proc, "pid", None), "pgid": os.getpgid(proc.pid) if hasattr(proc, "pid") and proc.pid else None}
        )

        async with self._lock:
            self.results.append(result)

        self.wha(f"PROBE_END {probe_id} exit={proc.returncode} dur={duration_ms:.0f}ms killed={killed}")
        return result

    async def race(self, probes: List[Tuple[str, int, str, Optional[Dict], Optional[str], bool]]) -> List[RaceResult]:
        """Run all probes in parallel race"""
        self.wha(f"RACE_START probes={len(probes)} max_parallel={self.max_probes}")
        semaphore = asyncio.Semaphore(self.max_probes)

        async def bounded_probe(pid, tier, cmd, env, cwd, unshare):
            async with semaphore:
                return await self._run_single(pid, tier, cmd, env, cwd, unshare)

        tasks = [bounded_probe(*p) for p in probes]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final = []
        for r in results:
            if isinstance(r, Exception):
                self.wha(f"RACE_EXCEPTION {r}")
                final.append(RaceResult(
                    probe_id="exception", tier=-1, cmd=str(r),
                    start_ts=0, end_ts=0, duration_ms=0,
                    exit_code=-1, stdout="", stderr=str(r),
                    killed=True, wha_moment=None, metadata={}
                ))
            else:
                final.append(r)

        self.wha(f"RACE_END completed={len(final)}")
        return final

    def to_parquet(self, path: str) -> bool:
        """Serialize results to parquet — but keep in memory if fs is lagging"""
        if not self.results:
            return False

        data = [asdict(r) for r in self.results]

        if HAS_PYARROW:
            # Build arrow table
            df_dict = {k: [d[k] for d in data] for k in data[0].keys()}
            # Convert dicts to JSON strings for complex fields
            for k in ["metadata"]:
                df_dict[k] = [json.dumps(v) for v in df_dict[k]]
            try:
                table = pa.table(df_dict)
                pq.write_table(table, path)
                return True
            except Exception as e:
                self.wha(f"PARQUET_FAIL {e}")

        # JSON fallback
        json_path = path.replace(".parquet", ".json")
        with open(json_path, "w") as f:
            json.dump(data, f, default=str, indent=2)
        return True

    def to_memory(self) -> Dict:
        """Return everything in memory for immediate analysis"""
        return {
            "results": [asdict(r) for r in self.results],
            "wha_log": self.wha_log,
            "timestamp": datetime.utcnow().isoformat(),
            "pyarrow": HAS_PYARROW
        }

# Kernel-level strace helper
async def kernel_strace_probe(target_pid: int, duration: float = 5.0) -> str:
    """Strace a target PID for N seconds, capture syscalls"""
    proc = await asyncio.create_subprocess_exec(
        "strace", "-p", str(target_pid), "-e", "trace=network,file,process",
        "-s", "256", "-o", "/dev/stdout",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    await asyncio.sleep(duration)
    proc.kill()
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8", errors="replace")

# Socket inspector
async def socket_probe() -> Dict:
    """Inspect all sockets on the system"""
    try:
        with open("/proc/net/tcp", "r") as f:
            tcp = f.read()
        with open("/proc/net/udp", "r") as f:
            udp = f.read()
        with open("/proc/net/unix", "r") as f:
            unix = f.read()
        return {"tcp": tcp[:5000], "udp": udp[:2000], "unix": unix[:2000]}
    except Exception as e:
        return {"error": str(e)}

# Git lock finder
async def git_lock_probe() -> Dict:
    """Find what is locking git operations"""
    results = {}
    # Check for index.lock files
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c", "find /mnt/agents/output -name 'index.lock' -o -name '*.lock' 2>/dev/null | head -20",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    results["lock_files"] = stdout.decode().strip().split("\n") if stdout else []

    # Check lsof for git-related files
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c", "lsof +D /mnt/agents/output 2>/dev/null | grep -i git | head -20 || echo 'NO_LSOF'",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    results["lsof_git"] = stdout.decode().strip()[:2000]

    # Check fuser
    proc = await asyncio.create_subprocess_exec(
        "bash", "-c", "fuser -v /mnt/agents/output/.git 2>/dev/null || echo 'NO_FUSER'",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    results["fuser"] = stdout.decode().strip()[:1000]

    return results

if __name__ == "__main__":
    glass = RaceGlass()
    print(f"[RACEGLASS] v3.14 ready | pyarrow={HAS_PYARROW} | timeout={RACE_TIMEOUT}s")
