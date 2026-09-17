#!/usr/bin/env python3
"""
pi-agent-client.py — Contact Pi Agent (or any remote command server) via argv.
Routes through Kimi sandbox internet tunnel → Tailscale → local machine.

Usage:
  python3 pi-agent-client.py pi "ls -la /home/toxic"
  python3 pi-agent-client.py pi "cat ~/.bashrc"
  python3 pi-agent-client.py pi "ps aux"
  python3 pi-agent-client.py grok "echo hello"  # if configured

Environment:
  PI_AGENT_URL      — default: https://awrawr-pc-1.tailc9ac71.ts.net/cmd
  PI_AGENT_TOKEN    — default: 3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio
  GROK_AGENT_URL    — grok endpoint (optional)
  GROK_AGENT_TOKEN  — grok token (optional)
"""
import argparse, json, os, sys, urllib.request, ssl
from pathlib import Path

# Default Pi Agent config (from user's Tailscale setup)
DEFAULT_PI_URL = "https://awrawr-pc-1.tailc9ac71.ts.net/cmd"
DEFAULT_PI_TOKEN = "3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio"

# Insecure SSL context for Tailscale self-signed certs
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def send_command(endpoint: str, token: str, command: str, timeout: int = 60):
    """Send a command to the remote agent and return response."""
    payload = json.dumps({"command": command}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "X-Command-Token": token,
            "Content-Type": "application/json",
            "User-Agent": "kimi-sandbox-pi-client/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read().decode()[:500]}
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Pi/Grok Agent argv wrapper")
    parser.add_argument("agent", choices=["pi", "grok"], help="Which agent to contact")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to execute (pass through)")
    args = parser.parse_args()

    if not args.command:
        print("[ERR] No command provided", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    cmd_str = " ".join(args.command)

    if args.agent == "pi":
        url = os.environ.get("PI_AGENT_URL", DEFAULT_PI_URL)
        token = os.environ.get("PI_AGENT_TOKEN", DEFAULT_PI_TOKEN)
    else:  # grok
        url = os.environ.get("GROK_AGENT_URL", "")
        token = os.environ.get("GROK_AGENT_TOKEN", "")
        if not url:
            print("[ERR] GROK_AGENT_URL not set", file=sys.stderr)
            sys.exit(1)

    print(f"[>] Sending to {args.agent}: {cmd_str[:80]}")
    result = send_command(url, token, cmd_str)

    if "error" in result:
        print(f"[ERR] {result['error']}")
        if "body" in result:
            print(result["body"])
        sys.exit(1)

    # Print stdout/stderr from remote
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    rc = result.get("returncode", -1)

    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)

    sys.exit(rc)

if __name__ == "__main__":
    main()
