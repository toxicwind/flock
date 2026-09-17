#!/usr/bin/env python3
"""RaceGlass v3.14-FINAL — 2.8s bulletproof asyncio race scaffold"""
import asyncio, os, json, time, signal, sys
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

RACE_TIMEOUT = 2.8
MAX_RACE_PROBES = 8

@dataclass
class RaceResult:
    probe_id: str; tier: int; cmd: str
    start_ts: float; end_ts: float; duration_ms: float
    exit_code: Optional[int]; stdout: str; stderr: str
    killed: bool; wha_moment: Optional[str]; metadata: Dict[str, Any]

class RaceGlass:
    def __init__(self, max_probes=MAX_RACE_PROBES, timeout=RACE_TIMEOUT):
        self.max_probes = max_probes; self.timeout = timeout
        self.results: List[RaceResult] = []
        self.wha_log: List[str] = []
        self._lock = asyncio.Lock()

    def wha(self, msg: str, data: Any = None):
        entry = f"[WHa {datetime.now(timezone.utc).isoformat()}] {msg}"
        if data: entry += f" | data={json.dumps(data, default=str)[:500]}"
        self.wha_log.append(entry); print(entry, file=sys.stderr)

    async def _run_single(self, probe_id: str, tier: int, cmd: str,
                          env: Optional[Dict] = None, cwd: Optional[str] = None,
                          use_unshare: bool = False) -> RaceResult:
        start = time.time()
        full_cmd = (["unshare", "-U", "-r", "bash", "-c", cmd]
                    if use_unshare and os.path.exists("/usr/bin/unshare")
                    else ["bash", "-c", cmd])
        self.wha(f"PROBE_START {probe_id}")
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})}, cwd=cwd,
                preexec_fn=os.setsid)

            # BULLETPROOF KILLER — NEVER LEAKS EXCEPTIONS
            async def killer():
                try:
                    await asyncio.sleep(self.timeout)
                    if proc.returncode is None:
                        try:
                            pgid = os.getpgid(proc.pid)
                            os.killpg(pgid, signal.SIGKILL)
                            self.wha(f"KILL_FIRED {probe_id} pgid={pgid}")
                        except (OSError, ProcessLookupError):
                            self.wha(f"KILL_NOOP {probe_id} dead")
                        except Exception as e:
                            self.wha(f"KILL_EXCEPT {probe_id} {e}")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.wha(f"KILL_FATAL {probe_id} {e}")

            killer_task = asyncio.create_task(killer())
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout + 1.0)
                killed = False
            except asyncio.TimeoutError:
                stdout, stderr = b"", b"TIMEOUT"
                killed = True
            finally:
                killer_task.cancel()
                try:
                    await killer_task
                except asyncio.CancelledError:
                    pass
                # Final cleanup
                if proc.returncode is None:
                    try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError): pass
                    except: pass
        except Exception as e:
            stdout, stderr = b"", f"SPAWN_ERROR: {e}".encode()
            killed = True
            proc = type("FakeProc", (), {"returncode": -1, "pid": -1})()

        end = time.time(); duration_ms = (end - start) * 1000
        out_str = stdout.decode("utf-8", errors="replace")[:8000]
        err_str = stderr.decode("utf-8", errors="replace")[:8000]
        wha = None
        for trigger in ["password", "token", "secret", "key=", "ssh", "portal",
                        "capability", "moonbox", "envd", "drive9", "overlay",
                        "blk-cube", "prod", "admin", "root", "sandbox", "ubuntu"]:
            if trigger in (out_str + err_str).lower():
                wha = f"TRIGGER:{trigger}"
                self.wha(f"WHa_MOMENT {probe_id} {trigger}")
                break
        result = RaceResult(
            probe_id=probe_id, tier=tier, cmd=cmd, start_ts=start, end_ts=end,
            duration_ms=duration_ms, exit_code=getattr(proc, "returncode", -1),
            stdout=out_str, stderr=err_str, killed=killed, wha_moment=wha,
            metadata={"pid": getattr(proc, "pid", None)})
        async with self._lock:
            self.results.append(result)
        self.wha(f"PROBE_END {probe_id} exit={getattr(proc, 'returncode', -1)} dur={duration_ms:.0f}ms")
        return result

    async def race(self, probes):
        self.wha(f"RACE_START n={len(probes)}")
        sem = asyncio.Semaphore(self.max_probes)
        async def bounded(p):
            async with sem:
                return await self._run_single(*p)
        tasks = [asyncio.create_task(bounded(p)) for p in probes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        final = []
        for r in results:
            if isinstance(r, Exception):
                self.wha(f"RACE_EXCEPT {r}")
                final.append(RaceResult("except", -1, str(r), 0, 0, 0, -1, "", str(r), True, None, {}))
            else:
                final.append(r)
        self.wha(f"RACE_END ok={len([x for x in final if not x.killed])}")
        return final

    def to_memory(self):
        return {"results": [asdict(r) for r in self.results],
                "wha_log": self.wha_log, "ts": datetime.now(timezone.utc).isoformat()}
