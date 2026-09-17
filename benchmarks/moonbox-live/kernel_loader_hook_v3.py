#!/usr/bin/env python3 -uS
"""
KERNEL LOADER HOOK v3 — Production-grade emergence controller
- Timeout → backgrounder (never kill on timeout)
- Portal traffic delimiting
- Parquet-first logging
- Autohook integration
"""

import os, sys, json, time, signal, threading, subprocess, traceback
from pathlib import Path
from datetime import datetime
import socket

# ── CONFIG ──────────────────────────────────────────────────────────────────
WORKSPACE = Path("/mnt/agents/output")
LOG_DIR = WORKSPACE / ".unlimited_logs"
PARQUET_DIR = WORKSPACE / ".parquet"
PID_DIR = WORKSPACE / ".bg_pids"
STATE_DIR = WORKSPACE / ".bg_state"
HOOK_LOG = WORKSPACE / ".hook.log"

for d in [LOG_DIR, PARQUET_DIR, PID_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LOGGING ─────────────────────────────────────────────────────────────────
def hook_log(msg, level="INFO"):
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(HOOK_LOG, "a") as f:
        f.write(line + "\n")
    return line

# ── TIMEOUT → BACKGROUNDER ──────────────────────────────────────────────────
class BackgroundExecutor:
    """When timeout hits, background the process instead of killing."""

    def __init__(self, name, cmd, env=None, cwd=None):
        self.name = name
        self.cmd = cmd
        self.env = {**os.environ, **(env or {}), "PYTHONUNBUFFERED": "1"}
        self.cwd = cwd or str(WORKSPACE)
        self.pid_file = PID_DIR / f"{name}.pid"
        self.log_file = LOG_DIR / f"{name}_{int(time.time())}.log"
        self.state_file = STATE_DIR / f"{name}.json"
        self.process = None
        self._bg_thread = None

    def start(self, timeout_sec=30):
        """Start process. If timeout hits, background it."""
        hook_log(f"[BG] Starting {self.name} (timeout={timeout_sec}s)")

        # Write initial state
        self._save_state({"status": "starting", "started_at": time.time(), "timeout": timeout_sec})

        # Start the process
        self.process = subprocess.Popen(
            self.cmd,
            shell=isinstance(self.cmd, str),
            stdout=open(self.log_file, "w"),
            stderr=subprocess.STDOUT,
            env=self.env,
            cwd=self.cwd,
            start_new_session=True,  # Detach from parent session
        )

        # Record PID
        with open(self.pid_file, "w") as f:
            f.write(str(self.process.pid))

        hook_log(f"[BG] {self.name} PID={self.process.pid}")

        # Wait with timeout
        try:
            rc = self.process.wait(timeout=timeout_sec)
            self._save_state({"status": "completed", "rc": rc, "completed_at": time.time()})
            hook_log(f"[BG] {self.name} completed (rc={rc})")
            return {"status": "completed", "rc": rc, "log": str(self.log_file)}

        except subprocess.TimeoutExpired:
            # TIMEOUT → BACKGROUND instead of kill
            hook_log(f"[BG] {self.name} timeout hit ({timeout_sec}s) → BACKGROUNDING", "WARN")
            self._background()
            return {
                "status": "backgrounded",
                "pid": self.process.pid,
                "log": str(self.log_file),
                "note": "Process backgrounded on timeout, not killed"
            }

    def _background(self):
        """Convert running process to background daemon."""
        self._save_state({
            "status": "backgrounded",
            "pid": self.process.pid,
            "backgrounded_at": time.time(),
            "log": str(self.log_file)
        })

        # Start a monitor thread that watches the process
        self._bg_thread = threading.Thread(target=self._monitor, daemon=True)
        self._bg_thread.start()

        hook_log(f"[BG] {self.name} now running in background (PID={self.process.pid})")

    def _monitor(self):
        """Monitor background process, restart if it dies."""
        while True:
            if self.process.poll() is not None:
                rc = self.process.returncode
                hook_log(f"[BG] {self.name} exited (rc={rc}), will restart", "WARN")
                time.sleep(2)
                # Restart
                self.process = subprocess.Popen(
                    self.cmd,
                    shell=isinstance(self.cmd, str),
                    stdout=open(self.log_file, "a"),
                    stderr=subprocess.STDOUT,
                    env=self.env,
                    cwd=self.cwd,
                    start_new_session=True,
                )
                with open(self.pid_file, "w") as f:
                    f.write(str(self.process.pid))
                hook_log(f"[BG] {self.name} restarted (PID={self.process.pid})")
            time.sleep(5)

    def _save_state(self, data):
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def stop(self):
        """Graceful stop (SIGTERM, then SIGKILL after 5s)."""
        if self.process and self.process.poll() is None:
            hook_log(f"[BG] Stopping {self.name} (SIGTERM)")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                hook_log(f"[BG] {self.name} force kill (SIGKILL)", "WARN")
                self.process.kill()
        self.pid_file.unlink(missing_ok=True)
        self._save_state({"status": "stopped", "stopped_at": time.time()})


# ── PORTAL DELIMITER ────────────────────────────────────────────────────────
class PortalDelimiter:
    """
    Delimits portal traffic to prevent frame bleeding.
    Uses length-prefixed framing for all portal messages.
    """

    HEADER_LEN = 8  # 8-byte hex length prefix
    MAX_FRAME = 1024 * 1024  # 1MB max frame

    @classmethod
    def encode(cls, data: bytes) -> bytes:
        """Encode data with length prefix."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        length = len(data)
        if length > cls.MAX_FRAME:
            raise ValueError(f"Frame too large: {length} > {cls.MAX_FRAME}")
        header = f"{length:08x}".encode("ascii")
        return header + data

    @classmethod
    def decode_stream(cls, sock: socket.socket) -> bytes:
        """Read one delimited frame from socket."""
        # Read 8-byte header
        header = b""
        while len(header) < cls.HEADER_LEN:
            chunk = sock.recv(cls.HEADER_LEN - len(header))
            if not chunk:
                raise ConnectionError("Portal disconnected")
            header += chunk

        length = int(header.decode("ascii"), 16)
        if length > cls.MAX_FRAME:
            raise ValueError(f"Frame too large: {length}")

        # Read payload
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(min(4096, length - len(payload)))
            if not chunk:
                raise ConnectionError("Portal disconnected mid-frame")
            payload += chunk

        return payload

    @classmethod
    def send_json(cls, sock: socket.socket, obj: dict) -> None:
        """Send JSON object over portal with delimiting."""
        data = json.dumps(obj).encode("utf-8")
        sock.sendall(cls.encode(data))

    @classmethod
    def recv_json(cls, sock: socket.socket) -> dict:
        """Receive JSON object from portal with delimiting."""
        payload = cls.decode_stream(sock)
        return json.loads(payload.decode("utf-8"))


# ── KERNEL CONNECTION ───────────────────────────────────────────────────────
class KernelLoader:
    """Loads and manages Jupyter kernel connection."""

    def __init__(self):
        self.conn_file = None
        self.conn_info = None
        self._find_kernel()

    def _find_kernel(self):
        """Auto-discover kernel connection file."""
        import glob
        patterns = [
            "/tmp/tmp*.json",
            "/tmp/kernel-*.json",
            "/tmp/conn-*.json",
        ]
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                self.conn_file = files[0]
                with open(self.conn_file) as f:
                    self.conn_info = json.load(f)
                hook_log(f"[KERNEL] Found connection: {self.conn_file}")
                return
        hook_log("[KERNEL] No kernel connection file found", "WARN")

    def get_conn(self) -> dict:
        return self.conn_info or {}

    def status(self) -> dict:
        return {
            "conn_file": self.conn_file,
            "conn_info": self.conn_info,
            "found": self.conn_info is not None,
        }


# ── AUTOHOOK INTEGRATION ────────────────────────────────────────────────────
def install_autohook():
    """Install autohook into current Python session."""
    import builtins

    original_print = builtins.print

    def hooked_print(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        # Log to file
        ts = datetime.utcnow().isoformat()
        with open(HOOK_LOG, "a") as f:
            f.write(f"[{ts}] [PRINT] {msg}\n")
        # Also call original
        return original_print(*args, **kwargs)

    builtins.print = hooked_print
    hook_log("[AUTOHOOK] print() patched")

    # Patch sys.excepthook
    def hooked_excepthook(exc_type, exc_value, exc_tb):
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        hook_log(f"[EXCEPTION] {tb_str}", "ERROR")
        # Still call default
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = hooked_excepthook
    hook_log("[AUTOHOOK] excepthook patched")


# ── MAIN CLI ────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Kernel Loader Hook v3")
    parser.add_argument("command", choices=["status", "bg", "portal-test", "kernel-status", "install-hook"])
    parser.add_argument("--name", default="task", help="Background task name")
    parser.add_argument("--cmd", default="", help="Command to run")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--host", default="127.0.0.1", help="Portal host")
    parser.add_argument("--port", type=int, default=25109, help="Portal port")
    args = parser.parse_args()

    if args.command == "status":
        # Show all background tasks
        print("=== BACKGROUND TASKS ===")
        for pid_file in sorted(PID_DIR.glob("*.pid")):
            name = pid_file.stem
            try:
                pid = int(pid_file.read_text().strip())
                alive = os.path.exists(f"/proc/{pid}")
                state_file = STATE_DIR / f"{name}.json"
                state = json.load(open(state_file)) if state_file.exists() else {}
                status = "RUNNING" if alive else "DEAD"
                print(f"  {name}: {status} (PID={pid}, state={state.get('status','unknown')})")
            except Exception as e:
                print(f"  {name}: ERROR ({e})")

    elif args.command == "bg":
        if not args.cmd:
            print("ERROR: --cmd required")
            sys.exit(1)
        exe = BackgroundExecutor(args.name, args.cmd)
        result = exe.start(timeout_sec=args.timeout)
        print(json.dumps(result, indent=2))

    elif args.command == "portal-test":
        # Test portal delimiting
        print(f"=== PORTAL DELIMITER TEST ({args.host}:{args.port}) ===")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((args.host, args.port))

            # Send health probe with delimiting
            PortalDelimiter.send_json(sock, {"action": "health", "ts": time.time()})

            # Receive response
            resp = PortalDelimiter.recv_json(sock)
            print(f"Response: {json.dumps(resp, indent=2)}")
            sock.close()
            print("PORTAL DELIMITER: OK")
        except Exception as e:
            print(f"PORTAL DELIMITER: FAIL ({e})")

    elif args.command == "kernel-status":
        kl = KernelLoader()
        print(json.dumps(kl.status(), indent=2))

    elif args.command == "install-hook":
        install_autohook()
        print("=== AUTOHOOK INSTALLED ===")
        print("print() and sys.excepthook patched")
        print("All output logged to:", HOOK_LOG)


if __name__ == "__main__":
    main()
