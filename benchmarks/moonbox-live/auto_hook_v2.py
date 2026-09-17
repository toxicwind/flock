#!/usr/bin/env python3
"""auto_hook_v2 — persistent background hook.
MITM subprocess calls, auto-commit, auto-push, env snapshot.
Runs detached. Survives session resets.
"""
import os, sys, subprocess, json, time, threading, pathlib, signal, hashlib

BASE = pathlib.Path("/mnt/agents/output")
LOG = BASE / ".bg_logs/auto_hook_v2.log"
TOOL_LOG = BASE / ".bg_logs/tool_mitm_v2.jsonl"
PID_FILE = BASE / ".bg_pids/auto_hook_v2.pid"
ENV_SNAPSHOT = BASE / "env_snapshot.json"
GIT_SYNC_INTERVAL = 60
PUSH_INTERVAL = 300

_ORIG_RUN = subprocess.run
_ORIG_POPEN = subprocess.Popen
_LOCK = threading.Lock()

def log(msg):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] {msg}\n"
    with open(LOG, 'a') as f:
        f.write(line)

def mitm_log(tool_type, cmd, rc, stdout, stderr, dt_ms):
    try:
        entry = {
            "ts": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "tool": tool_type,
            "cmd": str(cmd)[:2000],
            "rc": rc,
            "stdout_len": len(stdout) if stdout else 0,
            "stderr_len": len(stderr) if stderr else 0,
            "duration_ms": dt_ms,
            "pid": os.getpid()
        }
        with _LOCK:
            with open(TOOL_LOG, 'a') as f:
                f.write(json.dumps(entry) + '\n')
    except:
        pass

def _mitm_run(*args, **kwargs):
    t0 = time.time()
    try:
        result = _ORIG_RUN(*args, **kwargs)
    except Exception as e:
        dt = int((time.time() - t0) * 1000)
        cmd = args[0] if args else kwargs.get('args', 'unknown')
        mitm_log("shell_run_ERR", cmd, -1, "", str(e), dt)
        raise
    dt = int((time.time() - t0) * 1000)
    cmd = args[0] if args else kwargs.get('args', 'unknown')
    mitm_log("shell_run", cmd, result.returncode,
              result.stdout[:5000] if result.stdout else "",
              result.stderr[:2000] if result.stderr else "", dt)
    return result

def _mitm_popen(*args, **kwargs):
    t0 = time.time()
    try:
        proc = _ORIG_POPEN(*args, **kwargs)
    except Exception as e:
        dt = int((time.time() - t0) * 1000)
        cmd = args[0] if args else kwargs.get('args', 'unknown')
        mitm_log("shell_popen_ERR", cmd, -1, "", str(e), dt)
        raise
    dt = int((time.time() - t0) * 1000)
    cmd = args[0] if args else kwargs.get('args', 'unknown')
    mitm_log("shell_popen", cmd, 0, "", "", dt)
    return proc

def install_mitm():
    subprocess.run = _mitm_run
    subprocess.Popen = _mitm_popen
    log("MITM installed on subprocess.run and subprocess.Popen")

def snapshot_env():
    env = dict(os.environ)
    # Filter secrets
    filtered = {}
    for k, v in env.items():
        if any(s in k.lower() for s in ['pat', 'token', 'secret', 'key', 'password', 'auth']):
            filtered[k] = v[:4] + "***" + v[-4:] if len(v) > 8 else "***"
        else:
            filtered[k] = v
    with open(ENV_SNAPSHOT, 'w') as f:
        json.dump(filtered, f, indent=2, sort_keys=True)
    log(f"Env snapshot saved: {len(filtered)} vars")

def git_sync():
    repo = BASE / "paintball-field"
    if not (repo / ".git").exists():
        return
    try:
        os.chdir(repo)
        # Set remote with PAT
        pat = os.environ.get('GITHUB_PAT', '')
        if pat:
            subprocess.run(['git', 'remote', 'set-url', 'origin',
                f'https://toxicwind:{pat}@github.com/toxicwind/paintball-field.git'],
                capture_output=True, timeout=10)

        # Auto-commit any changes
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True, timeout=10)
        if result.stdout.strip():
            subprocess.run(['git', 'add', '-A'], capture_output=True, timeout=10)
            subprocess.run(['git', 'commit', '-m', f'auto_hook: sync {time.strftime("%Y%m%d-%H%M%S")}'],
                capture_output=True, timeout=10)
            log(f"Auto-committed {len(result.stdout.strip().split(chr(10)))} changes")

        # Push
        push_result = subprocess.run(['git', 'push', 'origin', 'main'],
            capture_output=True, text=True, timeout=30)
        if push_result.returncode == 0:
            log("Auto-push: SUCCESS")
        else:
            log(f"Auto-push: FAIL — {push_result.stderr[:200]}")
    except Exception as e:
        log(f"Git sync error: {e}")

def daemonize():
    if os.fork() > 0:
        sys.exit(0)
    os.setsid()
    if os.fork() > 0:
        sys.exit(0)
    os.chdir('/')
    os.umask(0)
    for fd in range(3):
        try:
            os.close(fd)
        except:
            pass
    os.open('/dev/null', os.O_RDONLY)
    os.open('/dev/null', os.O_WRONLY)
    os.dup2(1, 2)

def main():
    daemonize()
    PID_FILE.write_text(str(os.getpid()))
    log(f"auto_hook_v2 PID {os.getpid()} started")
    install_mitm()
    snapshot_env()

    last_git_sync = 0
    last_push = 0

    while True:
        now = time.time()
        if now - last_git_sync > GIT_SYNC_INTERVAL:
            git_sync()
            last_git_sync = now
        if now - last_push > PUSH_INTERVAL:
            snapshot_env()
            last_push = now
        time.sleep(10)

if __name__ == '__main__':
    main()
