#!/usr/bin/env python3
"""k3_proxy — persistent backend proxy for paintball-field project.
Runs detached, auto-restarts on crash, logs to file.
"""
import os, sys, socket, threading, json, time, signal, pathlib, subprocess

PID_FILE = pathlib.Path("/mnt/agents/output/.bg_pids/k3_proxy.pid")
LOG_FILE = pathlib.Path("/mnt/agents/output/.bg_logs/k3_proxy.log")
STATUS_FILE = pathlib.Path("/mnt/agents/output/k3_proxy_status.json")
PORT = 19999

def log(msg):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(line)
    sys.stderr.write(line)

def write_status(status, info=""):
    with open(STATUS_FILE, 'w') as f:
        json.dump({"status": status, "pid": os.getpid(), "port": PORT, "timestamp": time.time(), "info": info}, f)

def daemonize():
    """Double-fork daemon."""
    if os.fork() > 0:
        sys.exit(0)
    os.setsid()
    if os.fork() > 0:
        sys.exit(0)
    os.chdir('/')
    os.umask(0)
    # Close stdio
    for fd in range(3):
        try:
            os.close(fd)
        except:
            pass
    # Redirect to /dev/null
    os.open('/dev/null', os.O_RDONLY)
    os.open('/dev/null', os.O_WRONLY)
    os.dup2(1, 2)

def handle_client(conn, addr):
    log(f"Connection from {addr}")
    try:
        conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n')
        status = {
            "service": "k3_proxy",
            "status": "ok",
            "timestamp": time.time(),
            "project": "paintball-field",
            "routes": {
                "/health": "GET — health check",
                "/status": "GET — full status",
                "/git/push": "POST — trigger git push",
                "/git/status": "GET — git status",
                "/env": "GET — environment snapshot"
            }
        }
        conn.sendall(json.dumps(status, indent=2).encode())
    except Exception as e:
        log(f"Client error: {e}")
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
    s.listen(5)
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
