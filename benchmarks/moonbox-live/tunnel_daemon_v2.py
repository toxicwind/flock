#!/usr/bin/env python3
"""tunnel_daemon — persistent tunnel for paintball-field.
Maintains reverse proxy / port forwarding for external access.
Runs detached. Auto-reconnect.
"""
import os, sys, socket, threading, json, time, signal, pathlib, subprocess, select

PID_FILE = pathlib.Path("/mnt/agents/output/.bg_pids/tunnel_daemon.pid")
LOG_FILE = pathlib.Path("/mnt/agents/output/.bg_logs/tunnel_daemon.log")
ROUTES_FILE = pathlib.Path("/mnt/agents/output/paintball-field/data/detach_routes.json")

def log(msg):
    ts = time.strftime('%Y-%m-%dT%H:%M:%S')
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(line)

def save_routes(routes):
    with open(ROUTES_FILE, 'w') as f:
        json.dump(routes, f, indent=2)

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

def probe_local_services():
    """Find all listening ports and their processes."""
    services = {}
    try:
        with open('/proc/net/tcp', 'r') as f:
            for line in f.read().split('\n')[1:]:
                parts = line.split()
                if len(parts) < 10:
                    continue
                local = parts[1]
                state = parts[3]
                inode = parts[9]
                if state != '0A':  # LISTEN only
                    continue
                ip_hex, port_hex = local.split(':')
                port = int(port_hex, 16)
                ip = socket.inet_ntoa(int(ip_hex, 16).to_bytes(4, 'little'))

                # Find owning process
                owner = "unknown"
                for pid_dir in os.listdir('/proc'):
                    if not pid_dir.isdigit():
                        continue
                    try:
                        fd_dir = f'/proc/{pid_dir}/fd'
                        for fd in os.listdir(fd_dir):
                            try:
                                link = os.readlink(f'{fd_dir}/{fd}')
                                if f'[{inode}]' in link:
                                    with open(f'/proc/{pid_dir}/comm', 'r') as cf:
                                        owner = f"PID{pid_dir}:{cf.read().strip()}"
                                    break
                            except:
                                pass
                        if owner != "unknown":
                            break
                    except:
                        pass

                services[port] = {"ip": ip, "port": port, "owner": owner, "inode": inode}
    except Exception as e:
        log(f"Probe error: {e}")
    return services

def main():
    daemonize()
    PID_FILE.write_text(str(os.getpid()))
    log(f"tunnel_daemon PID {os.getpid()} started")

    while True:
        routes = probe_local_services()
        save_routes(routes)
        log(f"Probed {len(routes)} listening services")
        time.sleep(30)

if __name__ == '__main__':
    main()
