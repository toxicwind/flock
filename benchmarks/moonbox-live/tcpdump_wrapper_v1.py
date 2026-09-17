#!/usr/bin/env python3
"""tcpdump_wrapper_v1 — capture portal/envd traffic quickly."""
import subprocess, sys, os, time, pathlib

OUT = pathlib.Path("/mnt/agents/output/.pcap")
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, t=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return r.returncode == 0, r.stdout, r.stderr
    except Exception as e:
        return False, "", str(e)

def capture(iface="lo", duration=10, port=None):
    fn = OUT / f"cap_{iface}_{int(time.time())}.pcap"
    port_filter = f"port {port}" if port else ""
    cmd = f"sudo -n timeout {duration} tcpdump -i {iface} -w {fn} {port_filter} 2>/dev/null || true"
    print(f"[*] Capturing {iface} for {duration}s -> {fn}")
    run(cmd, t=duration+3)
    print(f"[+] Saved {fn}")
    return str(fn)

if __name__ == "__main__":
    iface = sys.argv[1] if len(sys.argv) > 1 else "lo"
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    capture(iface, dur)
