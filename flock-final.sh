#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# flock-final.sh — install, run, and wire flock into your stack
# ═══════════════════════════════════════════════════════════════════════
# Flock is the rate-limit-aware NVIDIA NIM proxy (multi-key load balancing).
# This script replaces nim-proxy-final.sh: same behavior, final naming,
# native binary managed by pitchfork instead of a Docker container.
set -uo pipefail

PROXY_URL="http://127.0.0.1:8000/v1"
WIZARD_URL="http://127.0.0.1:8000/"
REPO="${FLOCK_REPO:-$HOME/projects/flock}"
BIN_DST="$HOME/.flock/flock"
DATA_DIR="$HOME/.flock-data"
PITCHFORK_TOML="$HOME/projects/sovereign-projects/pitchfork.toml"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  flock — rate-limit-aware NVIDIA NIM proxy                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo

# ─── Step 0: toolchain check ──────────────────────────────────────────
if ! command -v cargo >/dev/null 2>&1; then
  echo "  cargo not found. Installing rustup..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1090
  source "$HOME/.cargo/env" 2>/dev/null || true
fi
echo "  cargo: OK ($(cargo --version 2>/dev/null | head -1))"

# ─── Step 1: retire any legacy standalone containers/binaries ─────────
if command -v docker >/dev/null 2>&1; then
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^nim-proxy$'; then
    echo "  Legacy 'nim-proxy' container found. Removing (state lives in $DATA_DIR)..."
    docker rm -f nim-proxy 2>/dev/null || true
  fi
fi
if [ -x "$HOME/.nim-proxy/nim-proxy" ]; then
  echo "  NOTE: legacy $HOME/.nim-proxy/nim-proxy left untouched (archive, not active)."
fi

# ─── Step 2: build + install the flock binary ─────────────────────────
if [ ! -d "$REPO/proxy" ]; then
  echo "  FATAL: flock source not found at $REPO (set FLOCK_REPO=...)."
  exit 1
fi
echo "  Building flock (release)..."
(
  cd "$REPO/proxy" || exit 1
  cargo build --release 2>&1 | tail -3
)
mkdir -p "$(dirname "$BIN_DST")" "$DATA_DIR"
cp "$REPO/proxy/target/release/flock" "$BIN_DST"
chmod +x "$BIN_DST"
echo "  Installed: $BIN_DST"

# ─── Step 3: pitchfork daemon stanza (idempotent) ──────────────────────
if command -v pitchfork >/dev/null 2>&1; then
  if grep -q '^\[daemons\.flock\]' "$PITCHFORK_TOML" 2>/dev/null; then
    echo "  pitchfork stanza: present"
  else
    echo "  Adding pitchfork stanza..."
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
    echo "  pitchfork stanza: added"
  fi
  pitchfork start flock 2>&1 | tail -2 || true
else
  echo "  pitchfork not on PATH; starting flock directly..."
  if ! ss -ltn 'sport = :8000' 2>/dev/null | grep -q LISTEN; then
    setsid nohup env HOST=127.0.0.1 PORT=8000 DATA_DIR="$DATA_DIR" "$BIN_DST" \
      >> "$DATA_DIR/flock.log" 2>&1 < /dev/null &
  fi
fi

# ─── Step 4: wait for readiness ───────────────────────────────────────
echo "  Waiting for flock to come up..."
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$WIZARD_URL" 2>/dev/null || echo 000)
  if [ "$code" = "200" ] || [ "$code" = "302" ] || [ "$code" = "503" ]; then
    echo "  Flock is up (HTTP $code)"
    break
  fi
  sleep 1
  if [ "$i" = "30" ]; then
    echo "  FATAL: flock did not come up in 30s. Check: tail $DATA_DIR/flock.log"
    exit 1
  fi
done

# ─── Step 5: wizard ───────────────────────────────────────────────────
echo
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  ACTION REQUIRED — complete the first-run wizard              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo
echo "  1. Open in a browser:  $WIZARD_URL"
echo "  2. Create the superuser account (first visitor becomes superuser)"
echo "  3. Add your NIM API key(s) — paste each nvapi-… key, comma-separated"
echo "     for multiple keys (each key adds 40 RPM)"
echo "  4. The wizard mints your first client key (flock_… / npk_…) — COPY IT"
echo
echo "  When the wizard finishes, return here and paste the client key."
echo

read -rp "  Paste client key: " FLOCK_KEY

if [[ -z "$FLOCK_KEY" ]]; then
  echo "  Empty key. Aborting."
  exit 1
fi

# ─── Step 6: test the proxy with the client key ───────────────────────
echo
echo "  Testing flock with your key..."
resp=$(curl -s -X POST "${PROXY_URL}/chat/completions" \
  -H "Authorization: Bearer ${FLOCK_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"nvidia/nemotron-3-super-120b-a12b","messages":[{"role":"user","content":"reply only: FLOCK_OK"}],"max_tokens":10}' 2>&1)

if echo "$resp" | grep -q "FLOCK_OK"; then
  echo "  ✓ Flock works — model replied FLOCK_OK"
elif echo "$resp" | grep -q '"error"'; then
  echo "  ✗ Flock returned error:"
  echo "$resp" | head -c 500
  echo
  echo "  Aborting. Check daemon logs."
  exit 1
else
  echo "  ⚠ Unexpected response (first 300 chars):"
  echo "$resp" | head -c 300
fi

# ─── Step 7: wire everything to flock ─────────────────────────────────
echo
echo "  Wiring stack to flock..."

# 7a. Append flock vars to ~/.secrets (idempotent, via Python)
python3 <<PYEOF
from pathlib import Path
s = Path.home() / ".secrets"
text = s.read_text() if s.exists() else ""
lines = text.splitlines()

# Remove any prior flock/nim-proxy client-key block
keep = []
skip = False
for line in lines:
    ls = line.strip()
    if ls in ("# ─── nim-proxy (rate-limit-aware) ───",
              "# ─── nim-proxy client key ───",
              "# ─── flock (rate-limit-aware) ───",
              "# ─── flock client key ───"):
        skip = True
        continue
    if skip and line.startswith("export ") and ("PROXY" in line or "FLOCK" in line or "NVIDIA" in line or "ANTHROPIC" in line):
        continue
    if skip and ls == "":
        skip = False
    if not skip:
        keep.append(line)

key = """${FLOCK_KEY}"""
block = """
# ─── flock (rate-limit-aware) ───
export FLOCK_URL="http://127.0.0.1:8000/v1"
export FLOCK_API_KEY="%s"
export NIM_PROXY_URL="http://127.0.0.1:8000/v1"
export NIM_PROXY_API_KEY="%s"
export NIM_BASE_URL="http://127.0.0.1:8000/v1"
export NVIDIA_API_KEY="%s"
export NVIDIA_NIM_API_KEY="%s"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000/v1"
export ANTHROPIC_API_KEY="%s"
export ANTHROPIC_AUTH_TOKEN="%s"
""" % (key, key, key, key, key, key)
keep.append(block)
s.write_text("\n".join(keep) + "\n")
print(f"  ✓ updated {s}")
PYEOF

# 7b. Write OpenCode config pointing at flock
mkdir -p ~/.config/opencode
python3 <<PYEOF
import json
from pathlib import Path

cfg = {
  "$schema": "https://opencode.ai/config.json",
  "model": "flock/nvidia/nemotron-3-super-120b-a12b",
  "provider": {
    "flock": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "NVIDIA NIM (via flock)",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1",
        "apiKey": "${FLOCK_KEY}",
        "timeout": False
      },
      "models": {
        "nvidia/nemotron-3-super-120b-a12b": {"name": "Nemotron 3 Super"},
        "nvidia/nemotron-3-ultra-550b-a55b": {"name": "Nemotron 3 Ultra"},
        "deepseek-ai/deepseek-v4-pro": {"name": "DeepSeek V4 Pro"}
      }
    }
  }
}
p = Path.home() / ".config/opencode/opencode.json"
p.write_text(json.dumps(cfg, indent=2))
print(f"  ✓ wrote {p}")
PYEOF

# 7c. Write Nanocoder config pointing at flock
mkdir -p ~/.config/nanocoder
python3 <<PYEOF
import json
from pathlib import Path

cfg = {
  "providers": [{
    "name": "nvidia",
    "baseUrl": "http://127.0.0.1:8000/v1",
    "apiKey": "${FLOCK_KEY}",
    "models": [
      "nvidia/nemotron-3-super-120b-a12b",
      "nvidia/nemotron-3-ultra-550b-a55b"
    ],
    "contextWindow": 1000000
  }]
}
p = Path.home() / ".config/nanocoder/agents.config.json"
p.write_text(json.dumps(cfg, indent=2))
print(f"  ✓ wrote {p}")
PYEOF

# 7d. Sync config to tau engine workspace
ENGINE="$HOME/projects/sovereign-projects/tau/engine"
if [ -d "$ENGINE/.agent" ]; then
  cp ~/.config/opencode/opencode.json "$ENGINE/.agent/opencode.json" 2>/dev/null || true
  echo "  ✓ synced to $ENGINE/.agent/"
fi

# ─── Step 8: final verification ───────────────────────────────────────
echo
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  DONE                                                         ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo
echo "  Binary:     $BIN_DST"
echo "  Daemon:     pitchfork flock (auto-start)"
echo "  Dashboard:  $WIZARD_URL"
echo "  API:        $PROXY_URL"
echo
echo "  Reload shell:   set -a; . ~/.secrets; set +a"
echo
echo "  To add more keys later: open $WIZARD_URL → Settings → add nvapi-… keys"
echo "  Each additional key adds 40 RPM to the pool."
echo
