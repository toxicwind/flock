#!/usr/bin/env python3
"""Dynamic live data loader — collects from wss, grpc, portal, envd, s6, kernel, browser."""
import glob, json, os, subprocess, sys, time, uuid

OUT_DIR = "/mnt/agents/dot/live"
os.makedirs(OUT_DIR, exist_ok=True)

def run_cmd(cmd, timeout=10):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"

def collect_kernel():
    """Collect ZMQ kernel connection info."""
    conn_files = sorted(glob.glob("/tmp/tmp*.json"))
    data = {"files": conn_files, "connections": []}
    for f in conn_files:
        try:
            with open(f) as fh:
                cfg = json.load(fh)
            data["connections"].append({
                "file": f,
                "ip": cfg.get("ip"),
                "shell_port": cfg.get("shell_port"),
                "iopub_port": cfg.get("iopub_port"),
                "hb_port": cfg.get("hb_port"),
                "key_prefix": cfg.get("key", "")[:8] + "..." if cfg.get("key") else None,
                "transport": cfg.get("transport"),
            })
        except Exception as e:
            data["connections"].append({"file": f, "error": str(e)})
    return data

def collect_processes():
    """Collect agent processes."""
    ps = run_cmd("ps aux | grep -E 'python|bun|node|go|agent|kernel|browser|drive9' | grep -v grep")
    agents = []
    for line in ps.split("\n"):
        parts = line.split()
        if len(parts) >= 11:
            agents.append({
                "pid": parts[1],
                "cpu": parts[2],
                "mem": parts[3],
                "cmd": " ".join(parts[10:]),
            })
    return agents

def collect_envd():
    """Collect envd/portal state."""
    data = {}
    for path in ["/mnt/portal-overlay/.agent-gw.json", "/mnt/agents/output/.env.kimi", "/mnt/agents/dot/identity.json"]:
        try:
            with open(path) as f:
                data[os.path.basename(path)] = json.load(f)
        except:
            try:
                with open(path) as f:
                    data[os.path.basename(path)] = f.read()[:500]
            except Exception as e:
                data[os.path.basename(path)] = str(e)
    return data

def collect_s6():
    """Collect s6 service state."""
    return {
        "s6_dir": run_cmd("ls -la /etc/s6/ 2>/dev/null || ls -la /var/run/s6/ 2>/dev/null || echo 'no s6 dir'"),
        "services": run_cmd("s6-svstat /var/run/s6/services/* 2>/dev/null || echo 'no s6 services'"),
    }

def collect_browser():
    """Collect browser/CDP state."""
    return {
        "chrome_procs": run_cmd("pgrep -a chromium | head -5"),
        "cdp_ports": run_cmd("ss -tlnp | grep -E '9222|9223|6080|5901'"),
        "user_data": run_cmd("ls -la /tmp/chromium_user_data/ 2>/dev/null | head -10"),
    }

def collect_chat():
    """Collect multi-agent chat log."""
    chat_file = "/mnt/agents/output/AGENT_CHAT.jsonl"
    if os.path.exists(chat_file):
        with open(chat_file) as f:
            lines = f.readlines()
        return [json.loads(l) for l in lines if l.strip()][-20:]
    return []

def main():
    snapshot = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "uuid": str(uuid.uuid4()),
        "kernel": collect_kernel(),
        "processes": collect_processes(),
        "envd": collect_envd(),
        "s6": collect_s6(),
        "browser": collect_browser(),
        "chat": collect_chat(),
    }
    out_path = os.path.join(OUT_DIR, f"live_{int(time.time())}.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"[LIVE] Saved to {out_path}")
    # Also save latest symlink
    latest = os.path.join(OUT_DIR, "latest.json")
    if os.path.exists(latest):
        os.remove(latest)
    os.symlink(out_path, latest)
    return snapshot

if __name__ == "__main__":
    snap = main()
    print(json.dumps(snap, indent=2, default=str)[:2000])
