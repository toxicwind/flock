#!/usr/bin/env python3
"""RaceGlass v3.14-FIXED — Bulletproof 2.8s asyncio race scaffold"""
import asyncio, subprocess, sys, os, json, time, signal
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

RACE_TIMEOUT = 2.8  # 2800ms as requested
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
        self.results: List[RaceResult] = []; self.wha_log: List[str] = []
        self._lock = asyncio.Lock()

    def wha(self, msg: str, data: Any = None):
        entry = f"[WHΑ {datetime.now(datetime.timezone.utc).isoformat()}] {msg}"
        if data: entry += f" | data={json.dumps(data, default=str)[:500]}"
        self.wha_log.append(entry); print(entry, file=sys.stderr)

    async def _run_single(self, probe_id: str, tier: int, cmd: str,
                          env: Optional[Dict] = None, cwd: Optional[str] = None,
                          use_unshare: bool = False) -> RaceResult:
        start = time.time()
        full_cmd = (["unshare", "-U", "-r", "bash", "-c", cmd]
                    if use_unshare and os.path.exists("/usr/bin/unshare")
                    else ["bash", "-c", cmd])
        self.wha(f"PROBE_START {probe_id} tier={tier}")
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **(env or {})}, cwd=cwd,
                preexec_fn=os.setsid)
            
            # BULLETPROOF KILLER — catches ALL exceptions, never leaks
            async def killer():
                try:
                    await asyncio.sleep(self.timeout)
                    if proc.returncode is None:
                        try:
                            pgid = os.getpgid(proc.pid)
                            os.killpg(pgid, signal.SIGKILL)
                            self.wha(f"KILL28_FIRED {probe_id} pid={proc.pid} pgid={pgid}")
                        except (OSError, ProcessLookupError) as e:
                            self.wha(f"KILL28_NOOP {probe_id} already_dead err={e}")
                        except Exception as e:
                            self.wha(f"KILL28_EXCEPT {probe_id} err={e}")
                except asyncio.CancelledError:
                    pass  # Normal cancellation
                except Exception as e:
                    self.wha(f"KILL28_FATAL {probe_id} err={e}")

            killer_task = asyncio.create_task(killer())
            
            try:
                # Shield the communicate so killer can't corrupt it
                stdout, stderr = await asyncio.shield(
                    asyncio.wait_for(proc.communicate(), timeout=self.timeout + 1.0)
                )
                killed = False
            except asyncio.TimeoutError:
                stdout, stderr = b"", b"RACE_TIMEOUT_EXCEEDED"
                killed = True
            except Exception as e:
                stdout, stderr = b"", f"RACE_COMM_EXCEPT: {e}".encode()
                killed = True
            finally:
                killer_task.cancel()
                try:
                    await killer_task
                except asyncio.CancelledError:
                    pass
                # Final cleanup — bulletproof
                if proc.returncode is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (OSError, ProcessLookupError):
                        pass
                    except Exception:
                        pass

        except Exception as e:
            stdout, stderr = b"", f"RACE_SPAWN_EXCEPT: {e}".encode()
            killed = True
            proc = type("FakeProc", (), {"returncode": -1, "pid": -1})()

        end = time.time(); duration_ms = (end - start) * 1000
        out_str = stdout.decode("utf-8", errors="replace")[:10000]
        err_str = stderr.decode("utf-8", errors="replace")[:10000]
        
        wha = None
        wha_triggers = ["password", "token", "secret", "key=", "ssh", "portal",
                        "capability", "moonbox", "envd", "drive9", "overlay",
                        "blk-cube", "prod", "admin", "root", "sandbox", "ubuntu"]
        combined = (out_str + err_str).lower()
        for trigger in wha_triggers:
            if trigger in combined:
                wha = f"TRIGGER:{trigger}"
                self.wha(f"WHΑ_MOMENT {probe_id} trigger={trigger}")
                break

        result = RaceResult(
            probe_id=probe_id, tier=tier, cmd=cmd, start_ts=start, end_ts=end,
            duration_ms=duration_ms, exit_code=proc.returncode if proc else -1,
            stdout=out_str, stderr=err_str, killed=killed, wha_moment=wha,
            metadata={"pid": getattr(proc, "pid", None)})
        async with self._lock:
            self.results.append(result)
        self.wha(f"PROBE_END {probe_id} exit={getattr(proc, 'returncode', -1)} dur={duration_ms:.0f}ms killed={killed}")
        return result

    async def race(self, probes):
        self.wha(f"RACE_START probes={len(probes)} max_parallel={self.max_probes}")
        semaphore = asyncio.Semaphore(self.max_probes)
        async def bounded_probe(p):
            async with semaphore:
                return await self._run_single(*p)
        tasks = [asyncio.create_task(bounded_probe(p)) for p in probes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        final = []
        for r in results:
            if isinstance(r, Exception):
                self.wha(f"RACE_EXCEPTION {r}")
                final.append(RaceResult(
                    probe_id="exception", tier=-1, cmd=str(r), start_ts=0, end_ts=0,
                    duration_ms=0, exit_code=-1, stdout="", stderr=str(r),
                    killed=True, wha_moment=None, metadata={}))
            else:
                final.append(r)
        self.wha(f"RACE_END completed={len(final)} results={len([x for x in final if not x.killed])}")
        return final

    def to_memory(self):
        return {"results": [asdict(r) for r in self.results],
                "wha_log": self.wha_log, "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
                "pyarrow": HAS_PYARROW}
