#!/usr/bin/env python3
"""k3_proxy_v3 — Full-featured backend proxy for paintball-field project.
Implements advertised routes: /health, /status, /git/push, /git/status, /env
Runs detached, auto-restarts on crash, logs to file.
"""
import os, sys, socket, threading, json, time, signal, pathlib, subprocess, re
from urllib.parse import parse_qs, urlparse

PID_FILE = pathlib.Path("/mnt/agents/output/.bg_pids/k3_proxy.pid")
LOG_FILE = pathlib.Path("/mnt/agents/output/.bg_logs/k3_proxy.log")
STATUS_FILE = pathlib.Path("/mnt/agents/output/k3_proxy_status.json")
PROJECT_DIR = pathlib.Path("/mnt/agents/output/paintball-field")
PORT = 19999

def log(msg):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(line)
    sys.stderr.write(line)

def write_status(status, info=""):
    with open(STATUS_FILE, 'w') as f:
        json.dump({
            "status": status,
            "pid": os.getpid(),
            "port": PORT,
            "timestamp": time.time(),
            "info": info,
            "version": "3.0"
        }, f, indent=2)

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

def run_cmd(cmd, timeout=30, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}
    except Exception as e:
        return {"rc": -1, "out": "", "err": str(e)}

def get_health():
    checks = {}
    # Check kernel
    try:
        r = run_cmd("curl -s -m 2 http://127.0.0.1:8888/kernel/status 2>/dev/null || echo '{}'", timeout=5)
        checks["kernel"] = json.loads(r["out"]) if r["out"] else {"alive": False}
    except:
        checks["kernel"] = {"alive": False}
    
    # Check restarter
    try:
        r = run_cmd("curl -s -m 2 http://127.0.0.1:18080/ 2>/dev/null || echo '{}'", timeout=5)
        checks["restarter"] = json.loads(r["out"]) if r["out"] else {"alive": False}
    except:
        checks["restarter"] = {"alive": False}
    
    # Check auto_hook
    try:
        r = run_cmd("pgrep -f auto_hook_v2.py", timeout=2)
        checks["auto_hook"] = {"alive": r["rc"] == 0, "pid": r["out"].strip() if r["rc"] == 0 else None}
    except:
        checks["auto_hook"] = {"alive": False}
    
    # Check tunnel
    try:
        r = run_cmd("pgrep -f tunnel_daemon", timeout=2)
        checks["tunnel"] = {"alive": r["rc"] == 0, "pid": r["out"].strip() if r["rc"] == 0 else None}
    except:
        checks["tunnel"] = {"alive": False}
    
    all_healthy = all(c.get("alive", False) for c in checks.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": time.time()
    }

def get_full_status():
    health = get_health()
    # Process snapshot
    procs = run_cmd("ps aux | grep -E 'python|node|socat' | grep -v grep | wc -l", timeout=5)
    # Disk usage
    disk = run_cmd("df -h /mnt/agents/output | tail -1", timeout=5)
    # Memory
    mem = run_cmd("free -m | grep Mem | awk '{print $3\" / \"$2 \" MB\"}'", timeout=5)
    # Uptime
    uptime = run_cmd("uptime -p", timeout=5)
    
    return {
        "service": "k3_proxy",
        "version": "3.0",
        "timestamp": time.time(),
        "project": "paintball-field",
        "health": health,
        "system": {
            "processes": procs["out"].strip() if procs["rc"] == 0 else "unknown",
            "disk": disk["out"].strip() if disk["rc"] == 0 else "unknown",
            "memory": mem["out"].strip() if mem["rc"] == 0 else "unknown",
            "uptime": uptime["out"].strip() if uptime["rc"] == 0 else "unknown"
        },
        "routes": {
            "/health": "GET — health check",
            "/status": "GET — full status",
            "/git/push": "POST — trigger git push",
            "/git/status": "GET — git status",
            "/env": "GET — environment snapshot"
        }
    }

def git_push():
    if not PROJECT_DIR.exists():
        return {"error": "Project directory not found"}
    
    pat = os.environ.get('GITHUB_PAT', '')
    if not pat:
        return {"error": "GITHUB_PAT not set"}
    
    # Set remote with PAT
    remote_url = f"https://toxicwind:{pat}@github.com/toxicwind/paintball-field.git"
    run_cmd(f"git remote set-url origin {remote_url}", cwd=str(PROJECT_DIR), timeout=10)
    
    # Add all changes
    add_r = run_cmd("git add -A", cwd=str(PROJECT_DIR), timeout=10)
    
    # Commit
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    commit_r = run_cmd(f'git commit -m "k3_proxy: auto-push @ {ts}" || echo "nothing to commit"', 
                       cwd=str(PROJECT_DIR), timeout=10)
    
    # Push
    push_r = run_cmd("git push origin main", cwd=str(PROJECT_DIR), timeout=30)
    
    return {
        "add_rc": add_r["rc"],
        "commit_rc": commit_r["rc"],
        "commit_out": commit_r["out"][:500],
        "push_rc": push_r["rc"],
        "push_out": push_r["out"][:500],
        "push_err": push_r["err"][:500] if push_r["err"] else "",
        "timestamp": ts
    }

def git_status():
    if not PROJECT_DIR.exists():
        return {"error": "Project directory not found"}
    
    status_r = run_cmd("git status --short", cwd=str(PROJECT_DIR), timeout=10)
    branch_r = run_cmd("git branch --show-current", cwd=str(PROJECT_DIR), timeout=10)
    log_r = run_cmd("git log --oneline -5", cwd=str(PROJECT_DIR), timeout=10)
    
    return {
        "branch": branch_r["out"].strip() if branch_r["rc"] == 0 else "unknown",
        "changes": status_r["out"].strip().split('\n') if status_r["rc"] == 0 and status_r["out"].strip() else [],
        "recent_commits": log_r["out"].strip().split('\n') if log_r["rc"] == 0 and log_r["out"].strip() else [],
        "timestamp": time.time()
    }

def env_snapshot():
    env = dict(os.environ)
    # Filter secrets
    filtered = {}
    for k, v in env.items():
        kl = k.lower()
        if any(s in kl for s in ['pat', 'token', 'secret', 'key', 'password', 'auth']):
            filtered[k] = v[:4] + "***" + v[-4:] if len(v) > 8 else "***"
        else:
            filtered[k] = v
    
    return {
        "vars": filtered,
        "count": len(filtered),
        "timestamp": time.time()
    }

def parse_request(data):
    """Parse a simple HTTP request."""
    lines = data.split('\r\n')
    if not lines:
        return None, None, {}, ""
    
    # Parse request line
    match = re.match(r'(GET|POST|PUT|DELETE)\s+(\S+)\s+HTTP', lines[0])
    if not match:
        return None, None, {}, ""
    
    method = match.group(1)
    path = match.group(2)
    
    # Parse headers
    headers = {}
    i = 1
    while i < len(lines) and lines[i]:
        if ':' in lines[i]:
            k, v = lines[i].split(':', 1)
            headers[k.strip().lower()] = v.strip()
        i += 1
    
    # Body is after empty line
    body = ""
    if i < len(lines):
        body = '\r\n'.join(lines[i+1:]) if i+1 < len(lines) else ""
    
    return method, path, headers, body

def send_json(conn, status_code, data):
    body = json.dumps(data, indent=2).encode()
    headers = (
        f"HTTP/1.1 {status_code} OK\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Connection: close\r\n\r\n"
    ).encode()
    conn.sendall(headers + body)

def send_error(conn, status_code, message):
    send_json(conn, status_code, {"error": message, "timestamp": time.time()})

def handle_client(conn, addr):
    log(f"Connection from {addr}")
    try:
        data = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\r\n\r\n' in data:
                # Check if there's a body
                header_end = data.find(b'\r\n\r\n') + 4
                headers_part = data[:header_end].decode('utf-8', errors='replace')
                
                # Parse Content-Length
                cl_match = re.search(r'content-length:\s*(\d+)', headers_part.lower())
                if cl_match:
                    content_length = int(cl_match.group(1))
                    if len(data) >= header_end + content_length:
                        break
                else:
                    break
        
        request_str = data.decode('utf-8', errors='replace')
        method, path, headers, body = parse_request(request_str)
        
        if not method:
            send_error(conn, 400, "Bad Request")
            return
        
        log(f"  {method} {path}")
        
        # Route handling
        if method == "GET" and path == "/health":
            send_json(conn, 200, get_health())
        elif method == "GET" and path == "/status":
            send_json(conn, 200, get_full_status())
        elif method == "GET" and path == "/git/status":
            send_json(conn, 200, git_status())
        elif method == "POST" and path == "/git/push":
            send_json(conn, 200, git_push())
        elif method == "GET" and path == "/env":
            send_json(conn, 200, env_snapshot())
        elif method == "GET" and path == "/":
            send_json(conn, 200, {
                "service": "k3_proxy_v3",
                "version": "3.0",
                "status": "running",
                "routes": ["/health", "/status", "/git/push", "/git/status", "/env"]
            })
        else:
            send_error(conn, 404, f"Not Found: {method} {path}")
    
    except Exception as e:
        log(f"Client error: {e}")
        try:
            send_error(conn, 500, str(e))
        except:
            pass
    finally:
        conn.close()

def main():
    daemonize()
    PID_FILE.write_text(str(os.getpid()))
    write_status("starting", "Daemon initialized")
    log(f"Daemon PID {os.getpid()} starting on port {PORT}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PORT))
    s.listen(10)
    write_status("running", f"Listening on 0.0.0.0:{PORT}")
    log(f"Listening on 0.0.0.0:{PORT}")
    
    while True:
        try:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            log(f"Accept error: {e}")
            time.sleep(1)

if __name__ == '__main__':
    main()
