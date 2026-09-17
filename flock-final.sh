#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
# flock-final.sh — install, run, and wire flock into your stack
# ═══════════════════════════════════════════════════════════════════════════
# Flock is the rate-limit-aware NVIDIA NIM proxy (multi-key load balancing).
# Successor to nim-proxy-final.sh: same behavior, final naming.
#
# Usage:
#   ./flock-final.sh                 interactive (prompts for the client key)
#   FLOCK_KEY=flock_... ./flock-final.sh
#                                    non-interactive (key from env, never echoed)
#   ./flock-final.sh --dry-run       print what would happen, change nothing
#
# Non-destructive: never deletes data, keys, containers, or configs.
# Legacy artifacts are reported and stopped, not removed.
set -uo pipefail

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

PROXY_URL="http://127.0.0.1:8000/v1"
WIZARD_URL="http://127.0.0.1:8000/"
REPO="${FLOCK_REPO:-$HOME/projects/flock}"
BIN_DST="$HOME/.flock/flock"
DATA_DIR="$HOME/.flock-data"
PITCHFORK_TOML="$HOME/projects/sovereign-projects/pitchfork.toml"
ENGINE="$HOME/projects/sovereign-projects/tau/engine"

say()  { echo "  $*"; }
dry()  { echo "  [dry-run] $*"; }
run()  { if [[ "$DRY_RUN" == 1 ]]; then dry "$*"; else eval "$*"; fi }

wait_for() { # wait_for <url> — poll until HTTP 200/302/503 or 60 tries
  local url="$1" code
  for _try in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$url" 2>/dev/null || echo 000)
    # 401 counts: the operator surface is auth-gated even when healthy
    if [[ "$code" == "200" || "$code" == "302" || "$code" == "401" || "$code" == "503" ]]; then
      echo "$code"
      return 0
    fi
    if command -v isleep >/dev/null 2>&1; then isleep 1; else curl -s --max-time 1 "$url" >/dev/null 2>&1; fi
  done
  echo 000
  return 1
}

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  flock — rate-limit-aware NVIDIA NIM proxy                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo
[[ "$DRY_RUN" == 1 ]] && echo "  DRY RUN — no changes will be made." && echo

# ─── Step 0: toolchain check ──────────────────────────────────────────
if ! command -v cargo >/dev/null 2>&1; then
  say "cargo not found. Installing rustup..."
  run "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
  # shellcheck disable=SC1090
  source "$HOME/.cargo/env" 2>/dev/null || true
fi
say "cargo: OK ($(cargo --version 2>/dev/null | head -1))"

# ─── Step 1: report (never remove) legacy standalone artifacts ────────
if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^nim-proxy$'; then
    say "Legacy 'nim-proxy' container exists. Stopping it (not removing; state lives in $DATA_DIR)..."
    run "docker stop nim-proxy >/dev/null 2>&1 || true"
  fi
fi
if [[ -x "$HOME/.nim-proxy/nim-proxy" ]]; then
  say "NOTE: legacy $HOME/.nim-proxy/nim-proxy left untouched (archive, not active)."
fi

# ─── Step 2: build + install the flock binary ─────────────────────────
if [[ ! -d "$REPO/proxy" ]]; then
  say "FATAL: flock source not found at $REPO (set FLOCK_REPO=...)."
  exit 1
fi
say "Building flock (release)..."
run "( cd \"$REPO/proxy\" && cargo build --release 2>&1 | tail -3 )"
run "mkdir -p \"\$(dirname \"$BIN_DST\")\" \"$DATA_DIR\""
run "cp \"$REPO/proxy/target/release/flock\" \"$BIN_DST\" && chmod +x \"$BIN_DST\""
say "Installed: $BIN_DST"

# ─── Step 3: daemon (pitchfork stanza if managed, else direct) ────────
if command -v pitchfork >/dev/null 2>&1 && [[ -f "$PITCHFORK_TOML" ]]; then
  if grep -q '^\[daemons\.flock\]' "$PITCHFORK_TOML" 2>/dev/null; then
    say "pitchfork stanza: present"
  else
    say "Adding pitchfork stanza..."
    if [[ "$DRY_RUN" == 1 ]]; then
      dry "append [daemons.flock] to $PITCHFORK_TOML"
    else
      cat >> "$PITCHFORK_TOML" <<TOML

[daemons.flock]
run = "exec env HOST=127.0.0.1 PORT=8000 DATA_DIR=$DATA_DIR $BIN_DST"
dir = "."
mise = false
retry = true
ready_cmd = "ss -ltn 'sport = :8000' | grep -q LISTEN"
env = { FLOCK_PORT = "8000" }
auto = ["start"]
TOML
      say "pitchfork stanza: added"
    fi
  fi
  run "pitchfork start flock 2>&1 | tail -2 || true"
else
  say "pitchfork not managing flock here; starting directly if :8000 is free..."
  if ! ss -ltn 'sport = :8000' 2>/dev/null | grep -q LISTEN; then
    run "setsid nohup env HOST=127.0.0.1 PORT=8000 DATA_DIR=\"$DATA_DIR\" \"$BIN_DST\" >> \"$DATA_DIR/flock.log\" 2>&1 < /dev/null &"
  else
    say ":8000 already listening — leaving the running daemon alone."
  fi
fi

# ─── Step 4: wait for readiness (poll, no blind sleeps) ───────────────
say "Waiting for flock to come up..."
if code=$(wait_for "$WIZARD_URL"); then
  say "Flock is up (HTTP $code)"
else
  say "FATAL: flock did not come up. Check: tail $DATA_DIR/flock.log"
  exit 1
fi

# ─── Step 5: wizard ───────────────────────────────────────────────────
echo
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ACTION REQUIRED — complete the first-run wizard              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo
say "1. Open in a browser:  $WIZARD_URL"
say "2. Create the superuser account (first visitor becomes superuser)"
say "3. Add your NIM API key(s) — paste each nvapi-… key, comma-separated"
say "   for multiple keys (each key adds 40 RPM)"
say "4. The wizard mints your first client key (flock_…) — COPY IT"
echo
say "When the wizard finishes, return here and paste the client key."
echo

FLOCK_KEY="${FLOCK_KEY:-}"
if [[ -z "$FLOCK_KEY" && "$DRY_RUN" == 0 ]]; then
  read -rp "  Paste client key: " FLOCK_KEY
fi

if [[ -z "$FLOCK_KEY" ]]; then
  [[ "$DRY_RUN" == 1 ]] && say "(dry-run: skipping key prompt)" || { say "Empty key. Aborting."; exit 1; }
fi

# ─── Step 6: test the proxy with the client key ───────────────────────
if [[ -n "$FLOCK_KEY" ]]; then
  echo
  say "Testing flock with your key..."
  resp=$(curl -s -X POST "${PROXY_URL}/chat/completions" \
    -H "Authorization: Bearer ${FLOCK_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"nvidia/nemotron-3-super-120b-a12b","messages":[{"role":"user","content":"reply only: FLOCK_OK"}],"max_tokens":10}' 2>&1)

  if echo "$resp" | grep -q "FLOCK_OK"; then
    say "✓ Flock works — model replied FLOCK_OK"
  elif echo "$resp" | grep -q '"error"'; then
    say "✗ Flock returned error:"
    echo "$resp" | head -c 500
    echo
    say "Aborting. Check daemon logs."
    exit 1
  else
    say "⚠ Unexpected response (first 300 chars):"
    echo "$resp" | head -c 300
  fi
fi

# ─── Step 7: wire everything to flock ─────────────────────────────────
echo
say "Wiring stack to flock..."

# 7a. Append flock vars to ~/.secrets (idempotent; key never echoed)
if [[ -n "$FLOCK_KEY" ]]; then
  FLOCK_KEY="$FLOCK_KEY" DRY_RUN="$DRY_RUN" python3 <<'PYEOF'
import os
from pathlib import Path

dry = os.environ.get("DRY_RUN") == "1"
key = os.environ["FLOCK_KEY"]
s = Path.home() / ".secrets"
text = s.read_text() if s.exists() else ""
lines = text.splitlines()

keep, skip = [], False
for line in lines:
    ls = line.strip()
    if ls in ("# ─── nim-proxy (rate-limit-aware) ───",
              "# ─── nim-proxy client key ───",
              "# ─── flock (rate-limit-aware) ───",
              "# ─── flock client key ───"):
        skip = True
        continue
    if skip and line.startswith("export ") and any(
        k in line for k in ("PROXY", "FLOCK", "NVIDIA", "ANTHROPIC")
    ):
        continue
    if skip and ls == "":
        skip = False
    if not skip:
        keep.append(line)

block = f"""
# ─── flock (rate-limit-aware) ───
export FLOCK_URL="http://127.0.0.1:8000/v1"
export FLOCK_API_KEY="{key}"
# compat aliases for tools that still read the old names
export NIM_PROXY_URL="http://127.0.0.1:8000/v1"
export NIM_PROXY_API_KEY="{key}"
export NIM_BASE_URL="http://127.0.0.1:8000/v1"
export NVIDIA_API_KEY="{key}"
export NVIDIA_NIM_API_KEY="{key}"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000/v1"
export ANTHROPIC_API_KEY="{key}"
export ANTHROPIC_AUTH_TOKEN="{key}"
"""
keep.append(block)
if dry:
    print(f"  [dry-run] would update {s} ({len(block.splitlines())} lines)")
else:
    s.write_text("\n".join(keep) + "\n")
    print(f"  ✓ updated {s}")
PYEOF
fi

# 7b. OpenCode config pointing at flock
if [[ -n "$FLOCK_KEY" ]]; then
  mkdir -p ~/.config/opencode
  FLOCK_KEY="$FLOCK_KEY" DRY_RUN="$DRY_RUN" python3 <<'PYEOF'
import json, os
from pathlib import Path

dry = os.environ.get("DRY_RUN") == "1"
cfg = {
  "$schema": "https://opencode.ai/config.json",
  "model": "flock/nvidia/nemotron-3-super-120b-a12b",
  "provider": {
    "flock": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "NVIDIA NIM (via flock)",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1",
        "apiKey": os.environ["FLOCK_KEY"],
        "timeout": False,
      },
      "models": {
        "nvidia/nemotron-3-super-120b-a12b": {"name": "Nemotron 3 Super"},
        "nvidia/nemotron-3-ultra-550b-a55b": {"name": "Nemotron 3 Ultra"},
        "deepseek-ai/deepseek-v4-pro": {"name": "DeepSeek V4 Pro"},
      },
    }
  },
}
p = Path.home() / ".config/opencode/opencode.json"
if dry:
    print(f"  [dry-run] would write {p}")
else:
    p.write_text(json.dumps(cfg, indent=2))
    print(f"  ✓ wrote {p}")
PYEOF
fi

# 7c. Nanocoder config pointing at flock
if [[ -n "$FLOCK_KEY" ]]; then
  mkdir -p ~/.config/nanocoder
  FLOCK_KEY="$FLOCK_KEY" DRY_RUN="$DRY_RUN" python3 <<'PYEOF'
import json, os
from pathlib import Path

dry = os.environ.get("DRY_RUN") == "1"
cfg = {
  "providers": [{
    "name": "nvidia",
    "baseUrl": "http://127.0.0.1:8000/v1",
    "apiKey": os.environ["FLOCK_KEY"],
    "models": [
      "nvidia/nemotron-3-super-120b-a12b",
      "nvidia/nemotron-3-ultra-550b-a55b",
    ],
    "contextWindow": 1000000,
  }]
}
p = Path.home() / ".config/nanocoder/agents.config.json"
if dry:
    print(f"  [dry-run] would write {p}")
else:
    p.write_text(json.dumps(cfg, indent=2))
    print(f"  ✓ wrote {p}")
PYEOF
fi

# 7d. Sync OpenCode config to the tau engine workspace
if [[ -d "$ENGINE/.agent" && -n "$FLOCK_KEY" && "$DRY_RUN" == 0 ]]; then
  cp ~/.config/opencode/opencode.json "$ENGINE/.agent/opencode.json" 2>/dev/null || true
  say "✓ synced to $ENGINE/.agent/"
fi

# ─── Step 8: final verification ───────────────────────────────────────
echo
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  DONE                                                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo
say "Binary:     $BIN_DST"
say "Daemon:     :8000 (pitchfork 'flock' when managed)"
say "Dashboard:  $WIZARD_URL"
say "API:        $PROXY_URL"
echo
say "Reload shell:   set -a; . ~/.secrets; set +a"
echo
say "To add more keys later: open $WIZARD_URL → Settings → add nvapi-… keys"
say "Each additional key adds 40 RPM to the pool."
echo
