#!/usr/bin/env python3
import asyncio, json, os, sys, signal, socket
from datetime import datetime

ROOT = "/mnt/agents/output"
SOCK_PATH = f"{ROOT}/.worker.sock"
PID_PATH = f"{ROOT}/.bg_pids/worker.pid"
LOG_PATH = f"{ROOT}/.bg_logs/worker.log"
TASK_QUEUE = f"{ROOT}/.task_queue"

# Source .env file directly into os.environ
env_file = f"{ROOT}/.env"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k] = v

# Hardcode bun PATH — never rely on shell inheritance
os.environ['PATH'] = '/root/.bun/bin:' + os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')

def log(msg):
    ts = datetime.now().isoformat()
    line = f"[{ts}] {msg}\n"
    with open(LOG_PATH, "a") as f: f.write(line)
    print(line, end="")

async def handle_client(reader, writer):
    try:
        data = await reader.read(65536)
        task = json.loads(data.decode())
        task_id = task.get("id", f"task_{datetime.now().timestamp()}")
        log(f"TASK {task_id}: {task.get('type', 'unknown')}")
        os.makedirs(TASK_QUEUE, exist_ok=True)
        with open(f"{TASK_QUEUE}/{task_id}.json", "w") as f: json.dump(task, f)
        result = {"id": task_id, "status": "ok", "stdout": "", "stderr": "", "returncode": 0}
        env = {**os.environ, **task.get("env", {})}
        cwd = task.get("cwd", ROOT)
        if task.get("type") == "shell":
            proc = await asyncio.create_subprocess_shell(task["cmd"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd, env=env)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=task.get("timeout", 300))
            result["stdout"] = stdout.decode(errors="replace")[:100000]
            result["stderr"] = stderr.decode(errors="replace")[:100000]
            result["returncode"] = proc.returncode
        elif task.get("type") == "python":
            proc = await asyncio.create_subprocess_exec(sys.executable, "-c", task["code"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd, env=env)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=task.get("timeout", 300))
            result["stdout"] = stdout.decode(errors="replace")[:100000]
            result["stderr"] = stderr.decode(errors="replace")[:100000]
            result["returncode"] = proc.returncode
        elif task.get("type") == "bun":
            proc = await asyncio.create_subprocess_shell(task["cmd"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd, env=env)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=task.get("timeout", 300))
            result["stdout"] = stdout.decode(errors="replace")[:100000]
            result["stderr"] = stderr.decode(errors="replace")[:100000]
            result["returncode"] = proc.returncode
        elif task.get("type") == "git_push":
            cwd = task.get("cwd", f"{ROOT}/app")
            for cmd in [["git","add","-A"], ["git","commit","-m",task.get("message","auto")], ["git","push","origin",task.get("branch","main")]]:
                proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd, env=env)
                stdout, stderr = await proc.communicate()
            result["stdout"] = stdout.decode(errors="replace")
            result["stderr"] = stderr.decode(errors="replace")
        else:
            result["status"] = "error"
            result["stderr"] = f"Unknown type: {task.get('type')}"
        with open(f"{TASK_QUEUE}/{task_id}.done", "w") as f: json.dump(result, f)
        writer.write(json.dumps(result).encode())
        await writer.drain()
        log(f"TASK {task_id}: done rc={result['returncode']}")
    except Exception as e:
        log(f"ERROR: {e}")
        writer.write(json.dumps({"status":"error","stderr":str(e)}).encode())
        await writer.drain()
    finally:
        writer.close()

async def main():
    os.makedirs(f"{ROOT}/.bg_pids", exist_ok=True)
    os.makedirs(f"{ROOT}/.bg_logs", exist_ok=True)
    os.makedirs(TASK_QUEUE, exist_ok=True)
    try: os.remove(SOCK_PATH)
    except: pass
    with open(PID_PATH, "w") as f: f.write(str(os.getpid()))
    server = await asyncio.start_unix_server(handle_client, SOCK_PATH)
    log(f"WORKER STARTED pid={os.getpid()} sock={SOCK_PATH}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    if os.fork(): sys.exit(0)
    os.setsid()
    if os.fork(): sys.exit(0)
    sys.stdout.flush(); sys.stderr.flush()
    with open("/dev/null", "r") as f: os.dup2(f.fileno(), sys.stdin.fileno())
    with open(LOG_PATH, "a+") as f: os.dup2(f.fileno(), sys.stdout.fileno()); os.dup2(f.fileno(), sys.stderr.fileno())
    asyncio.run(main())
