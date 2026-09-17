#!/usr/bin/env python3
"""
Obtuse Workaround: HTTP-over-Tailscale-Serve Interactive Shell Bridge.
Instead of fixing tailscale in the kimi container, we use the REMOTE's
already-working tailscale serve (/cmd endpoint) as our shell transport.
This is a reverse-maintenance channel: kimi sends commands TO awrawr-pc-1
via HTTPS, awrawr-pc-1 executes them and returns JSON.
"""
import urllib.request, urllib.error, json, ssl, sys, os, readline, base64, shlex

REMOTE = "https://awrawr-pc-1.tailc9ac71.ts.net/cmd"
TOKEN = "3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def run(cmd: str, timeout: int = 30):
    """Send a command to awrawr-pc-1 and return (stdout, stderr, rc)."""
    data = json.dumps({"command": cmd}).encode()
    req = urllib.request.Request(
        REMOTE,
        data=data,
        headers={
            "X-Command-Token": TOKEN,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, context=CTX, timeout=timeout)
        body = json.loads(resp.read().decode())
        return body.get("output", ""), body.get("error", ""), body.get("return_code", -1)
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}: {e.read().decode()[:200]}", e.code
    except Exception as e:
        return "", str(e), -1

def interactive():
    """Interactive shell loop."""
    print("=== SHELL BRIDGE TO awrawr-pc-1 ===")
    print("Type commands. 'exit' to quit. 'audit' to run full audit.")
    print("")
    while True:
        try:
            cmd = input("awrawr-pc-1$ ")
        except EOFError:
            break
        if cmd.strip() == "exit":
            break
        if cmd.strip() == "audit":
            full_audit()
            continue
        out, err, rc = run(cmd)
        if out:
            print(out, end="")
        if err:
            print(f"[stderr] {err}", file=sys.stderr)
        if rc != 0:
            print(f"[rc={rc}]")

def full_audit():
    """Run the full maintenance audit on awrawr-pc-1."""
    checks = [
        ("hostname && whoami && pwd", "Identity"),
        ("cat ~/.bashrc | head -50", "bashrc top"),
        ("ls -la ~/projects/ 2>/dev/null || echo 'no projects dir'", "Projects dir"),
        ("ls -la ~/projects/pi-agent/ 2>/dev/null | head -20 || echo 'no pi-agent'", "pi-agent"),
        ("ls -la ~/projects/zed/ 2>/dev/null | head -20 || echo 'no zed'", "zed"),
        ("ls -la ~/projects/grok/ 2>/dev/null | head -20 || echo 'no grok'", "grok"),
        ("tailscale status 2>&1 | head -10", "Tailscale status"),
        ("df -h /home", "Disk usage"),
        ("ps aux | grep -E 'python|node|npm' | grep -v grep | head -10", "Running processes"),
    ]
    for cmd, label in checks:
        print(f"\n=== {label} ===")
        out, err, rc = run(cmd)
        print(out if out else "(no output)")
        if err:
            print(f"ERR: {err}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "audit":
        full_audit()
    else:
        interactive()
