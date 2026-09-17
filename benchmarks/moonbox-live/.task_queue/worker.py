import socket, json, os, subprocess, sys
SOCK = "/mnt/agents/output/.worker.sock"
LOG = "/mnt/agents/output/.bg_logs/worker.log"
os.environ["PATH"] = "/root/.bun/bin:" + os.environ.get("PATH", "")

def log(msg):
    with open(LOG, "a") as f: f.write(f"[{os.getpid()}] {msg}\n")

try: os.remove(SOCK)
except: pass
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(SOCK)
os.chmod(SOCK, 0o777)
s.listen(5)
s.settimeout(1.0)
log("STARTED")

while True:
    try:
        conn, _ = s.accept()
    except socket.timeout:
        continue
    try:
        data = conn.recv(65536)
        if not data:
            conn.close()
            continue
        task = json.loads(data.decode())
        tid = task.get("id", "?")
        log(f"TASK {tid}: {task.get('type', '?')}")
        result = {"status": "ok", "stdout": "", "stderr": "", "returncode": 0}
        env = {**os.environ, **task.get("env", {})}
        cwd = task.get("cwd", "/mnt/agents/output")
        timeout = task.get("timeout", 300)
        try:
            if task.get("type") == "shell":
                p = subprocess.run(task["cmd"], shell=True, capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
            elif task.get("type") == "python":
                p = subprocess.run([sys.executable, "-c", task["code"]], capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
            elif task.get("type") == "bun":
                p = subprocess.run(["/root/.bun/bin/bun"] + task.get("args", []), capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
            elif task.get("type") == "git":
                p = subprocess.run(["git", "--git-dir=/mnt/agents/output/.triangle-git-metadata", "--work-tree=/mnt/agents/output/triangle-access"] + task.get("args", []), capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
            else:
                result = {"status": "error", "stderr": "unknown type", "returncode": 1}
                conn.sendall(json.dumps(result).encode())
                conn.close()
                continue
            result["stdout"] = p.stdout[:50000]
            result["stderr"] = p.stderr[:50000]
            result["returncode"] = p.returncode
        except subprocess.TimeoutExpired:
            result = {"status": "error", "stderr": f"TIMEOUT after {timeout}s", "returncode": -1}
        except Exception as e:
            result = {"status": "error", "stderr": str(e), "returncode": -1}
        conn.sendall(json.dumps(result).encode())
        log(f"TASK {tid}: done rc={result['returncode']}")
    except Exception as e:
        log(f"CONN ERROR: {e}")
    finally:
        try: conn.close()
        except: pass
