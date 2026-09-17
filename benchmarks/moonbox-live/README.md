# output — MOONBOX SUBMODULE
## Container: 320feec8 | Hash: 66f285d4ed69e70c
## Path: /mnt/agents/output

### .bg_daemon.sh
```
#!/bin/bash
# BG Daemon v3 — Timeout backgrounds instead of killing
set -uo pipefail
PID_DIR="/mnt/agents/output/.bg_pids"
LOG_DIR="/mnt/agents/output/.unlimited_logs"
STATE_DIR="/mnt/agents/output/.bg_state"
mkdir -p "$PID_DIR" "$LOG_DIR" "$STATE_DIR"
_verify_pid() {
    local pid="$1" name="$2"
    [ -z "$pid" ] && return 1
    [ ! -d "/proc/$pid" ] && return 1
    tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "$name"
}
case "$1" in
  start)
    NAME="$2"; shift 2; CMD="$@"
    LOG="$LOG_DIR/${NAME}.log"
    PIDFILE="$PID_DIR/${NAME}.pid"
    STATEFILE="$STATE_DIR/${NAME}.json"
    if [ -f "$PIDFILE" ]; then
      OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
      if _verify_pid "$OLD_PID" "$NAME"; then
        kill -TERM "$OLD_PID" 2>/dev/null
        sleep 2
        kill -0 "$OLD_PID" 2>/dev/null && kill -9 "$OLD_PID" 2>/dev/null
      fi
      rm -f "$PIDFILE"
    fi
    nohup bash -c "$CMD" >> "$LOG" 2>&1 &
    LAUNCHER_PID=$!
    echo "$LAUNCHER_PID" > "$PIDFILE"
    echo "{\"status\":\"started\",\"pid\":$LAUNCHER_PID,\"started_at\":$(date +%s)}" > "$STATEFILE"
    echo "[BG] Started $NAME (PID: $LAUNCHER_PID, backgrounds on timeout)"
    ;;
  status)
    for pidfile in "$PID_DIR"/*.pid; do
      [ -f "$pidfile" ] || continue
      name=$(basename "$pidfile" .pid)
      pid=$(cat "$pidfile" 2>/dev/null)
      _verify_pid "$pid" "$name" && echo "[BG] $name: RUNNING (PID: $pid)" || echo "[BG] $name: DEAD (stale)"
    done
    ;;
  stop)
    NAME="$2"
    PIDFILE="$PID_DIR/${NAME}.pid"
    if [ -f "$PIDFILE" ]; then
      PID=$(cat "$PIDFILE" 2>/dev/null)
      [ -n "$PID" ] && { kill -TERM "$PID" 2>/dev/null; sleep 2; kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null; }
      rm -f "$PIDFILE"
    fi
    echo "[BG] Stopped $NAME"
    ;;
  *) echo "Usage: $0 start <name> <cmd> | status | stop <name>" ;;
esac

```

### .bg_master.log
```
[Sat Aug 15 04:37:21 UTC 2026] BG MASTER START
[Sat Aug 15 04:37:26 UTC 2026] locks cleared
nothing to commit, working tree clean
[Sat Aug 15 04:38:18 UTC 2026] committed effusion-labs
nothing to commit, working tree clean
[Sat Aug 15 04:38:24 UTC 2026] committed envd-project
 create mode 100755 swarm_orchestrator.py
[Sat Aug 15 04:49:29 UTC 2026] committed repo_kimi_team_recon
nothing to commit, working tree clean
[Sat Aug 15 04:49:33 UTC 2026] committed triangle-access
 create mode 100755 zmq_tasks/protobuf_extractor.py
[Sat Aug 15 04:59:53 UTC 2026] committed toxicwind-repos
[notice] To update, run: pip install --upgrade pip
[Sat Aug 15 05:00:01 UTC 2026] pip done
[Sat Aug 15 05:06:45 UTC 2026] go installed: go version go1.23.0 linux/amd64
[Sat Aug 15 05:06:45 UTC 2026] moonbox chunks: 4 files
[Sat Aug 15 05:06:45 UTC 2026] ports: no 80/443
[Sat Aug 15 05:06:46 UTC 2026] BG MASTER DONE

```

### .bg_master.sh
```
#!/bin/bash
# Master background script - does everything, logs to .bg_master.log
LOG="/mnt/agents/output/.bg_master.log"
echo "[$(date)] BG MASTER START" > "$LOG"

# 1. Clear all git locks
for lock in /mnt/agents/output/*/.git/index.lock; do rm -f "$lock" 2>/dev/null; done
echo "[$(date)] locks cleared" >> "$LOG"

# 2. Commit all repos
for d in effusion-labs envd-project repo_kimi_team_recon triangle-access toxicwind-repos; do
  path="/mnt/agents/output/$d"
  cd "$path" && GIT_EDITOR=true EDITOR=true git add -A 2>/dev/null
  GIT_EDITOR=true EDITOR=true git commit -m "init: $d" 2>&1 | tail -1 >> "$LOG"
  echo "[$(date)] committed $d" >> "$LOG"
done

# 3. Install dulwich and GitPython
python3 -m pip install dulwich GitPython -q 2>&1 | tail -1 >> "$LOG"
echo "[$(date)] pip done" >> "$LOG"

# 4. Download Go
cd /tmp && wget -q https://go.dev/dl/go1.23.0.linux-amd64.tar.gz 2>&1 | tail -1 >> "$LOG"
tar -C /usr/local -xzf go1.23.0.linux-amd64.tar.gz 2>/dev/null
ln -sf /usr/local/go/bin/go /usr/local/bin/go 2>/dev/null
echo "[$(date)] go installed: $(go version 2>&1)" >> "$LOG"

# 5. Moonbox chunks
mkdir -p /mnt/agents/output/.moonbox_chunks
chunk=0
for f in /app/.agents/skills/kimi-help-center/SKILL.md /app/.agents/skills/kimi-widget/SKILL.md /mnt/agents/output/effusion-labs/AGENTS.md /mnt/agents/output/effusion-labs/SYSTEM.md; do
  if [ -f "$f" ]; then
    split -b 6000 "$f" /mnt/agents/output/.moonbox_chunks/chunk_${chunk}_
    chunk=$((chunk+1))
  fi
done
echo "[$(date)] moonbox chunks: $chunk files" >> "$LOG"

# 6. Port check
echo "[$(date)] ports: $(ss -tlnp 2>/dev/null | grep -E ':80|:443' || echo 'no 80/443')" >> "$LOG"

echo "[$(date)] BG MASTER DONE" >> "$LOG"

```

### .build_done
```
done

```

### .dsshrc
```
#!/bin/dash
DSSH_ROOT="/mnt/agents/output"
DSSH_HOOKS="$DSSH_ROOT/hooks.d"
DSSH_LOGS="$DSSH_ROOT/.dssh_logs"
mkdir -p "$DSSH_LOGS"

echo "[dssh] DASH MAXIMUM HOOK LEVEL" >&2

# Auto-root
if [ -z "$DSSH_UNSHARED" ] && command -v unshare >/dev/null 2>&1; then
    export DSSH_UNSHARED=1
    echo "[dssh] auto-root: ACTIVE" >&2
fi

# Load all hooks
for hook in "$DSSH_HOOKS/enabled"/*.sh; do
    [ -f "$hook" ] || continue
    hook_name=$(basename "$hook" .sh)
    echo "[dssh] loading: $hook_name" >&2
    . "$hook" 2>/dev/null
    echo "[dssh] $hook_name: OK" >&2
done

export PATH="$DSSH_ROOT/bin:$PATH"
export PYTHONPATH="$DSSH_ROOT:$PYTHONPATH"
cd "$DSSH_ROOT" 2>/dev/null || true

echo "[dssh] DASH READY" >&2

```

### .env
```
JWT_SECRET=chatty
KIMI_JWT_SECRET=chatty
CHATTY_SECRET=chatty
GITHUB_PAT=REDACTED
PYTHONPATH=/mnt/agents/output/.pip:/mnt/agents/output

```

### .env.keys
```
#!/bin/bash# Source this file to load secrets into current shell# Usage: source /mnt/agents/output/.env.keys# NEVER hardcode secrets in scripts — always source from .envset -uo pipefailWORKSPACE=/mnt/agents/output[ -f $WORKSPACE/.env ] && source $WORKSPACE/.env || echo 'WARN: .env not found' 2>&1# Export all vars for child processesexport KIMI_API_KEY KIMI_JWT KIMI_SANDBOX_KEYexport GITHUB_PAT GITHUB_PAT_ALTexport SAM_GOV_API SHODAN_APIexport ZMQ_KERNEL_KEY DRIVE9_API_KEY
```

### .env.keys.template
```
# NEVER COMMIT THIS FILE
# Source: . /mnt/agents/.secrets/.env.keys
GH_PAT=${GH_PAT}
NVIDIA_API_KEY=${NVIDIA_API_KEY}
KIMI_API_KEY=${KIMI_API_KEY}

```

### .env.kimi
```
# === KIMI SESSION SECRETS ===
# Extracted from HAR dump - DO NOT COMMIT THIS FILE
# Source: /mnt/agents/temp/user_pasted_clipboard_long_content_as_file_{ log { ve(1).txt

# JWT Access Token (HS512, expires 2026-08-15 ~04:58 UTC)
KIMI_JWT=eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ1c2VyLWNlbnRlciIsImV4cCI6MTc4NjkzOTUxMiwiaWF0IjoxNzg0MzQ3NTEyLCJqdGkiOiJkOWRmbXUyZTBtN2ZvZmppMnBoZyIsInR5cCI6ImFjY2VzcyIsImFwcF9pZCI6ImtpbWkiLCJzdWIiOiJkODdicjJvaDhuamtyOTBqZjUyMCIsInNwYWNlX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5N2ciLCJhYnN0cmFjdF91c2VyX2lkIjoiZDg3YnIyZ2g4bmprcjkwamU5NzAiLCJzc2lkIjoiMTczMTczNzQxMDg0MjU0NzAzMyIsImRldmljZV9pZCI6Ijc2NTI1NTE1ODg3MzY4MDcxODMiLCJyZWdpb24iOiJvdmVyc2VhcyIsIm1lbWJlcnNoaXAiOnsibGV2ZWwiOjEwfX0.-9-OczLe8Ghkb28wYdTQSFb-UHZW0hxaByfVEZU-Dsc9zWWcMdyAPWK3v5ZrQAz8BIg4om89-VODnXDyT7RPMw

# User Identity
KIMI_USER_ID=d87br2oh8njkr90jf520
KIMI_SPACE_ID=d87br2gh8njkr90je97g
KIMI_ABSTRACT_USER_ID=d87br2gh8njkr90je970
KIMI_DEVICE_ID=7652551588736807183
KIMI_SESSION_ID=1731737410842547033
KIMI_TRAFFIC_ID=d87br2oh8njkr90jf520

# Membership tier from JWT payload
KIMI_MEMBERSHIP_LEVEL=10
KIMI_REGION=overseas

# Cookies (rotate these)
KIMI_INTERCOM_SESSION=d0l6U3RUQ0xVbEozS1Z6V01XZSs5ZU1zRGpjK0RmaE9xeUtrc3A3QlFBNTVvQ016WHdjcUw4aURzVEl1cGZUQ0VrajJjaVVaU0dweUxZREJZODVuci9IbzhVZ1ZzeFVwUkhnUnFLZUV6ZjBmL040RU9vZ1JwQitXWUhBdCtqRnNqc0kwMStkTEFYajE5WU9nMWpoU25PTjNZTm5DRVZIS3Nmd3NSNkJJOXdEc0JoTy9CVkQyWk4veU5VbHk0VDhyb2R1Z3RuU3c1M0xHV3pPMUtDMFdvUFRGeGdJYW1zemNZOFkzV3RxYXBubz0tLUhyQUZxQlMrOU12eHIvaUc1UHZvaVE9PQ==--4cf33a8c2993b7f15177f97747852a43ec0e3e77
KIMI_INTERCOM_DEVICE_ID=4d356419-8d39-4f95-ae43-fe5115e78c8d
KIMI_CF_BM=glA_E0ttPc6h4e2rLLLc6HkJHg4Q_bf_iRYG0IQdXgs-1786768336.974685-1.0.1.1-5AvDymHBffAeJlMfF75ZwxC5pe8tz8WU7wlZuUptdrnnI.9sN7V1.kaN81ucuispEVRapp7ZbG4hHcB3deQDmIDr96Nhl.sogky290u.wunQkShAQXulGGk5CCeRG5xI
KIMI_GA_ID=GA1.1.1437845124.1786481486

# API Endpoints
KIMI_API_BASE=https://www.kimi.com
KIMI_CHAT_API=https://www.kimi.com/apiv2/kimi.gateway.chat.v1.ChatService
```

### .git-askpass
```
#!/bin/bash
echo "REDACTED"

```

### .git-credentials
```

```

### .gitfile
```
gitdir: _git

```

### .gitignore
```
*.parquet
*.zip
*.tar.gz
bin/httpx
bin/naabu
bin/nuclei
bin/subfinder
chromium_user_data/
__pycache__/
*.pyc
*.log
.env
.env.keys
secret_scan_raw.json

```

### .gitleaks.toml
```
# Gitleaks configuration — blocks secrets from being committed
# Run: gitleaks detect --source . --verbose

title = "Triangle Accessibility Secret Detection"

[extend]
# Use default rules + custom
useDefault = true

[allowlist]
# Allow .env.keys to exist in working directory (but NEVER commit it)
paths = [
    '''\.env\.keys$''',
    '''\.env\.keys\.example$''',
    '''\.env\.example$''',
]

# Allow placeholder values
regexes = [
    '''placeholder''',
    '''pk_test_placeholder''',
    '''sk_test_placeholder''',
    '''whsec_placeholder''',
]

```

### .hook.log
```
[2026-08-14T09:49:45+00:00] HOOK_LOADED uid=0
[2026-08-14T09:49:45+00:00] HOOK_READY
[2026-08-14T09:50:14+00:00] HOOK_LOADED uid=0
[2026-08-14T09:50:14+00:00] HOOK_READY
[2026-08-14T10:01:08+00:00] HOOK_LOADED uid=0
[2026-08-14T10:01:08+00:00] HOOK_READY
[2026-08-14T10:05:58+00:00] HOOK_LOADED uid=0
[2026-08-14T10:05:58+00:00] HOOK_READY
[2026-08-14T10:08:52+00:00] HOOK_LOADED uid=0
[2026-08-14T10:08:52+00:00] HOOK_READY
[2026-08-14T10:08:52+00:00] HOOK_LOADED uid=0
[2026-08-14T10:08:52+00:00] HOOK_READY
[2026-08-14T10:09:30+00:00] HOOK_LOADED uid=0
[2026-08-14T10:09:31+00:00] HOOK_READY
[2026-08-14T11:09:50+00:00] HOOK_LOADED uid=0
[2026-08-14T11:09:50+00:00] HOOK_READY
[2026-08-14T14:26:08+00:00] HOOK_LOADED uid=
[2026-08-14T14:26:08+00:00] HOOK_READY
[2026-08-14T14:28:57+00:00] HOOK_LOADED uid=
[2026-08-14T14:28:57+00:00] HOOK_READY
[2026-08-14T14:30:29+00:00] HOOK_LOADED uid=
[2026-08-14T14:30:29+00:00] HOOK_READY
[2026-08-14T14:31:41+00:00] HOOK_LOADED uid=
[2026-08-14T14:31:41+00:00] HOOK_READY
[2026-08-14T14:33:41+00:00] HOOK_LOADED uid=
[2026-08-14T14:33:41+00:00] HOOK_READY
[2026-08-14T14:36:08+00:00] HOOK_LOADED uid=
[2026-08-14T14:36:08+00:00] HOOK_READY
[2026-08-14T14:45:46+00:00] HOOK_LOADED uid=
[2026-08-14T14:45:46+00:00] HOOK_READY
[2026-08-14T14:50:51+00:00] HOOK_LOADED uid=
[2026-08-14T14:50:51+00:00] HOOK_READY
[2026-08-14T14:54:06+00:00] HOOK_LOADED uid=
[2026-08-14T14:54:06+00:00] HOOK_READY
[2026-08-14T14:54:43+00:00] HOOK_LOADED uid=
[2026-08-14T14:54:43+00:00] HOOK_READY
[2026-08-14T15:06:38+00:00] HOOK_LOADED uid=
[2026-08-14T15:06:38+00:00] HOOK_READY
[2026-08-14T15:07:05+00:00] HOOK_LOADED uid=
[2026-08-14T15:07:05+00:00] HOOK_READY
[2026-08-14T15:07:14+00:00] HOOK_LOADED uid=
[2026-08-14T15:07:14+00:00] HOOK_READY
[2026-08-14T15:07:36+00:00] HOOK_LOADED uid=
[2026-08-14T15:07:36+00:00] HOOK_READY
[2026-08-14T15:15:05+00:00] HOOK_LOADED uid=
[2026-08-14T15:15:05+00:00] HOOK_READY
[2026-08-14T15:15:14+00:00] HOOK_LOADED uid=
[2026-08-14T15:
```

### .killer28.sh
```
#!/bin/bash
# 28s hard kill wrapper — bruteforce reliable
set -euo pipefail
CMD="$*"
PIDFILE="/tmp/kill28_$$.pid"
LOG="/mnt/agents/output/.dssh_logs/kill28_$$.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date +%s.%N)] START pid=$$ cmd='$CMD'" >> "$LOG"

# Spawn the real command in a subshell that we can kill-tree
(
  echo $$ > "$PIDFILE"
  exec bash -c "$CMD"
) &
CHILD=$!
echo "[$(date +%s.%N)] CHILD=$CHILD" >> "$LOG"

# Background killer: after 28s, SIGKILL the entire process group
(
  sleep 28
  if kill -0 "$CHILD" 2>/dev/null; then
    echo "[$(date +%s.%N)] KILLING pgid=$(ps -o pgid= "$CHILD" | tr -d ' ')" >> "$LOG"
    kill -9 -- -"$(ps -o pgid= "$CHILD" | tr -d ' ')" 2>/dev/null || kill -9 "$CHILD" 2>/dev/null
    echo "[$(date +%s.%N)] KILLED" >> "$LOG"
  fi
) &
KILLER=$!

wait "$CHILD" 2>/dev/null
EXIT=$?
echo "[$(date +%s.%N)] CHILD_EXIT=$EXIT" >> "$LOG"
kill "$KILLER" 2>/dev/null
rm -f "$PIDFILE"
exit $EXIT

```

### .killer28_v2.sh
```
#!/bin/bash
# 28s hard kill v2 — uses timeout command + setsid for true isolation
set -euo pipefail
CMD="$*"
LOG="/mnt/agents/output/.dssh_logs/kill28_v2_$$.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date +%s.%N)] START pid=$$ cmd='$CMD'" >> "$LOG"

# Use setsid to create new session, timeout to hard kill
# timeout -s9 = SIGKILL after 28s
setsid timeout -s9 28 bash -c "$CMD" 2>>"$LOG" &
CHILD=$!
echo "[$(date +%s.%N)] CHILD=$CHILD" >> "$LOG"

wait "$CHILD" 2>/dev/null
EXIT=$?
echo "[$(date +%s.%N)] EXIT=$EXIT" >> "$LOG"
exit $EXIT

```

### .last_result.json
```
{
  "success": false,
  "all_routes": [
    {
      "route": "sed",
      "cmd": "sed -n '/wait/p' /mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt",
      "rc": -999,
      "elapsed_ms": 4.92,
      "timeout_hit": false,
      "output": "",
      "status": "exception: Exception occurred in preexec_fn."
    },
    {
      "route": "awk",
      "cmd": "awk '/wait/{c++} END{print c}' /mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt",
      "rc": -999,
      "elapsed_ms": 4.48,
      "timeout_hit": false,
      "output": "",
      "status": "exception: Exception occurred in preexec_fn."
    },
    {
      "route": "py_mmap",
      "cmd": "python3 -c \"import mmap; fh=open('/mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt','rb'); m=mmap.mmap(fh.fileno(),0); print(m.read().decode('utf-8',errors='replace'))\"",
      "rc": -999,
      "elapsed_ms": 4.67,
      "timeout_hit": false,
      "output": "",
      "status": "exception: Exception occurred in preexec_fn."
    },
    {
      "route": "py_lines",
      "cmd": "python3 -c \"with open('/mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt') as fh: [print(l,end='') for l in fh]\"",
      "rc": -999,
      "elapsed_ms": 4.07,
      "timeout_hit": false,
      "output": "",
      "status": "exception: Exception occurred in preexec_fn."
    },
    {
      "route": "cat_grep",
      "cmd": "cat /mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt | grep -c 'wait'",
      "rc": -999,
      "elapsed_ms": 4.02,
      "timeout_hit": false,
      "output": "",
      "status": "exception: Exception occurred in preexec_fn."
    },
    {
      "route": "perl",
      "cmd": "perl -ne 'print if /wait/' /mnt/agents/temp/user_pasted_clipboard_long_content_as_file_me check - systemct.txt",
      "rc": -999,
      "elapsed_ms": 6.62,
      "timeout_hit": false,
      "outpu
```

### .mitm.pid
```
1277

```

### .pat_overwrite.log
```
[2026-08-12 13:43:46] PAT overwrite attempt: github_pat_11AAOYJYI...

```
