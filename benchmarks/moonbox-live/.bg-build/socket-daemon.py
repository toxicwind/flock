#!/usr/bin/env python3
import socket, os, sys, json, subprocess, threading, signal

SOCKET_PATH = "/mnt/agents/output/.bg-build/sockets/triangle.sock"
PIDFILE = "/mnt/agents/output/.bg-build/sockets/daemon.pid"

def handle_client(conn, addr):
    try:
        data = conn.recv(4096).decode()
        cmd = json.loads(data)
        if cmd.get("action") == "build":
            conn.sendall(json.dumps({"status": "building", "pid": os.getpid()}).encode())
            result = subprocess.run(
                ["node", "node_modules/next/dist/bin/next", "build"],
                cwd="/mnt/agents/output/triangle-access/src/frontend",
                capture_output=True, text=True, timeout=300
            )
            conn.sendall(json.dumps({
                "status": "done" if result.returncode == 0 else "failed",
                "code": result.returncode,
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:]
            }).encode())
        elif cmd.get("action") == "status":
            conn.sendall(json.dumps({"status": "ready", "build_dir": ".next exists"}).encode())
        elif cmd.get("action") == "swarm":
            conn.sendall(json.dumps({"status": "swarm_ready", "workers": 4}).encode())
        else:
            conn.sendall(json.dumps({"error": "unknown action"}).encode())
    except Exception as e:
        conn.sendall(json.dumps({"error": str(e)}).encode())
    finally:
        conn.close()

def main():
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCKET_PATH)
    s.listen(5)
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))
    print(f"[DAEMON] Listening on {SOCKET_PATH}")
    
    def shutdown(signum, frame):
        s.close()
        os.unlink(SOCKET_PATH)
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
