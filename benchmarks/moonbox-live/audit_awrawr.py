#!/usr/bin/env python3
"""
MAXIMAL AUDIT of awrawr-pc-1 via command server + SSH fallback.
Saves everything to files, handles truncation, auto-paginates.
"""
import subprocess, json, os, sys, time, textwrap, urllib.request, ssl, base64
from pathlib import Path

# ─── CONFIG ───
REMOTE = "https://awrawr-pc-1.tailc9ac71.ts.net/cmd"
TOKEN = "3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio"
SSH_KEY = """-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACD5naVVgXiwUUeapmUFHgOsxZbiCOSSxMttGmeWm81JPwAAAJhIW9wzSFvc
MwAAAAtzc2gtZWQyNTUxOQAAACD5naVVgXiwUUeapmUFHgOsxZbiCOSSxMttGmeWm81JPw
AAAEBIQPqUcMjbuvhIkzL/UzwtsaBR7pGB+c/Yj586SLbLKfmdpVWBeLBRR5qmZQUeA6zF
luII5JLEy20aZ5abzUk/AAAAE3RhaWxzY2FsZS1hd3Jhd3ItcGMBAg==
-----END OPENSSH PRIVATE KEY-----"""
OUTDIR = Path("/mnt/agents/output/audit_awrawr")
OUTDIR.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 9000  # split files at ~9k chars

# ─── SSL CONTEXT (skip verification for tailscale serve) ───
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ─── COMMAND SERVER CLIENT ───
def rcmd(cmd, timeout=30):
    """Run command on awrawr-pc-1 via HTTPS command server."""
    try:
        req = urllib.request.Request(
            REMOTE,
            data=json.dumps({"command": cmd}).encode(),
            headers={"X-Command-Token": TOKEN, "Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, context=CTX, timeout=timeout)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"output": "", "error": str(e), "return_code": -1}

# ─── SSH CLIENT (fallback) ───
def sshcmd(cmd, timeout=30):
    """Run command via SSH with tailscale key."""
    keyfile = Path.home() / ".ssh" / "tailscale_id"
    if not keyfile.exists():
        keyfile.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        keyfile.write_text(SSH_KEY)
        keyfile.chmod(0o600)
    ssh = [
        "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=accept-new",
        "-i", str(keyfile), "toxic@100.72.199.93", cmd
    ]
    try:
        r = subprocess.run(ssh, capture_output=True, text=True, timeout=timeout)
        return {"output": r.stdout, "error": r.stderr, "return_code": r.returncode}
    except Exception as e:
        return {"output": "", "error": str(e), "return_code": -1}

# ─── HYBRID: try SSH first, fallback to command server ───
def run_remote(cmd, timeout=30):
    r = sshcmd(cmd, timeout)
    if r["return_code"] == 0 and not r["error"]:
        return r
    return rcmd(cmd, timeout)

# ─── FILE WRITER WITH AUTO-CHUNKING ───
def save(label, content):
    """Save content to file, auto-split at CHUNK_SIZE."""
    base = OUTDIR / label.replace("/", "_").replace(" ", "_")
    if len(content) <= CHUNK_SIZE:
        base.with_suffix(".txt").write_text(content)
        print(f"  [SAVE] {base.name}.txt ({len(content)} chars)")
        return
    # Split into chunks
    chunks = textwrap.wrap(content, width=CHUNK_SIZE, replace_whitespace=False, drop_whitespace=False)
    for i, chunk in enumerate(chunks):
        chunkfile = base.with_suffix(f".{i:03d}.txt")
        chunkfile.write_text(chunk)
        print(f"  [SAVE] {chunkfile.name} ({len(chunk)} chars)")

# ─── AUDIT COMMANDS ───
AUDITS = [
    ("identity", "hostname && whoami && id && pwd && echo '---' && uname -a"),
    ("env", "env | sort"),
    ("bashrc", "cat ~/.bashrc"),
    ("bash_profile", "cat ~/.bash_profile 2>/dev/null || cat ~/.profile 2>/dev/null || echo 'no profile'"),
    ("bash_aliases", "cat ~/.bash_aliases 2>/dev/null || echo 'no aliases'"),
    ("ssh_config", "cat ~/.ssh/config 2>/dev/null || echo 'no ssh config'"),
    ("ssh_keys", "ls -la ~/.ssh/"),
    ("processes", "ps aux"),
    ("processes_tree", "ps auxf"),
    ("services", "systemctl list-units --type=service --state=running 2>/dev/null || service --status-all 2>/dev/null || echo 'no systemd'"),
    ("crontab", "crontab -l 2>/dev/null || echo 'no crontab'"),
    ("cron_d", "ls -la /etc/cron.d/ 2>/dev/null; cat /etc/cron.d/* 2>/dev/null"),
    ("listening_ports", "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'no ss/netstat'"),
    ("iptables", "sudo iptables -L -n 2>/dev/null || iptables -L -n 2>/dev/null || echo 'no iptables'"),
    ("docker_ps", "docker ps -a 2>/dev/null || echo 'no docker'"),
    ("docker_images", "docker images 2>/dev/null || echo 'no docker'"),
    ("mounts", "mount | sort"),
    ("fstab", "cat /etc/fstab"),
    ("df", "df -h"),
    ("disk_usage_home", "du -sh ~/* 2>/dev/null | sort -h"),
    ("tailscale_status", "tailscale status"),
    ("tailscale_netcheck", "tailscale netcheck 2>/dev/null || echo 'no netcheck'"),
    ("tailscale_serve", "tailscale serve status 2>/dev/null || echo 'no serve'"),
    ("tailscale_funnel", "tailscale funnel status 2>/dev/null || echo 'no funnel'"),
    ("tailscale_ip", "tailscale ip"),
    ("tailscale_prefs", "tailscale debug prefs 2>/dev/null || echo 'no debug'"),
    ("projects_dir", "ls -la ~/projects/ 2>/dev/null || ls -la /home/*/projects/ 2>/dev/null || echo 'no projects dir'"),
    ("pi_agent_structure", "find ~/projects/pi-agent -type f -name '*.ts' -o -name '*.js' -o -name '*.json' 2>/dev/null | head -100"),
    ("pi_agent_package", "cat ~/projects/pi-agent/packages/coding-agent/package.json 2>/dev/null || echo 'no package.json'"),
    ("pi_agent_src_top", "ls -la ~/projects/pi-agent/packages/coding-agent/src/ 2>/dev/null || echo 'no src'"),
    ("zed_structure", "find ~/projects/zed -type f 2>/dev/null | head -50 || echo 'no zed'"),
    ("grok_structure", "find ~/projects/grok -type f 2>/dev/null | head -50 || echo 'no grok'"),
    ("npm_global", "npm list -g --depth=0 2>/dev/null || echo 'no npm global'"),
    ("node_version", "node --version 2>/dev/null; npm --version 2>/dev/null"),
    ("python_version", "python3 --version; pip3 --version 2>/dev/null || echo 'no pip3'"),
    ("pip_list", "pip3 list 2>/dev/null | head -30 || echo 'no pip3'"),
    ("cargo_version", "cargo --version 2>/dev/null || echo 'no cargo'"),
    ("rustc_version", "rustc --version 2>/dev/null || echo 'no rustc'"),
    ("go_version", "go version 2>/dev/null || echo 'no go'"),
    ("git_config", "git config --global --list 2>/dev/null || echo 'no git config'"),
    ("git_repos", "find ~ -name '.git' -type d 2>/dev/null | head -20"),
    ("history", "history 2>/dev/null | tail -50 || cat ~/.bash_history 2>/dev/null | tail -50 || echo 'no history'"),
    ("sudoers", "sudo -l 2>/dev/null || echo 'no sudo'"),
    ("users", "cat /etc/passwd | grep -E 'bash|sh'"),
    ("groups", "groups"),
    ("env_files", "find ~ -name '.env' -o -name '*.env' 2>/dev/null | head -20"),
    ("secrets_grep", r"grep -ri 'password\|secret\|token\|api_key' ~/.config/ 2>/dev/null | head -20 || echo 'no secrets found'"),
    ("tmux_sessions", "tmux ls 2>/dev/null || echo 'no tmux'"),
    ("screen_sessions", "screen -ls 2>/dev/null || echo 'no screen'"),
    ("nvidia", "nvidia-smi 2>/dev/null || echo 'no nvidia'"),
    ("lspci", "lspci 2>/dev/null | head -10 || echo 'no lspci'"),
    ("meminfo", "cat /proc/meminfo | head -10"),
    ("cpuinfo", "cat /proc/cpuinfo | grep 'model name' | head -5"),
    ("uptime", "uptime"),
    ("last_login", "last -10 2>/dev/null || echo 'no last'"),
]

# ─── MAIN ───
def main():
    print("=" * 70)
    print("AWRAWR-PC-1 MAXIMAL AUDIT")
    print("=" * 70)
    
    # Test connectivity
    print("\n[TEST] Connectivity...")
    r = run_remote("whoami")
    if r["return_code"] == 0:
        print(f"  Connected as: {r['output'].strip()}")
        save("00_identity", f"whoami: {r['output']}\nrc: {r['return_code']}\nerror: {r['error']}")
    else:
        print(f"  WARNING: Remote connectivity failed: {r['error']}")
        print("  Continuing with local-only audits and retrying remote...")
        save("00_identity", f"whoami: FAILED\nrc: {r['return_code']}\nerror: {r['error']}")
    
    # Run all audits
    for label, cmd in AUDITS:
        print(f"\n[AUDIT] {label}...")
        r = run_remote(cmd, timeout=30)
        output = f"=== COMMAND ===\n{cmd}\n\n=== OUTPUT ===\n{r['output']}\n\n=== STDERR ===\n{r['error']}\n\n=== RC ===\n{r['return_code']}\n"
        save(label, output)
    
    # Summary
    print("\n" + "=" * 70)
    print("AUDIT COMPLETE")
    print("=" * 70)
    files = list(OUTDIR.iterdir())
    print(f"Files saved: {len(files)}")
    total_size = sum(f.stat().st_size for f in files if f.is_file())
    print(f"Total size: {total_size} bytes")
    print(f"Output dir: {OUTDIR}")
    
    # List all saved files
    print("\n[SAVED FILES]")
    for f in sorted(files):
        if f.is_file():
            print(f"  {f.name}: {f.stat().st_size} bytes")

if __name__ == "__main__":
    main()
