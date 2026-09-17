#!/usr/bin/env bash
# fix_bashrc.sh — Fix .bashrc for pi and grok to use project forks
# Run on the Tailscale PC: bash /home/toxic/fix_bashrc.sh

set -euo pipefail

BASHRC="$HOME/.bashrc"
PROJECTS="$HOME/projects"
PI_DIR="$PROJECTS/pi-agent"
GROK_DIR="$PROJECTS/grok"

# Backup original
if [[ ! -f "$BASHRC.backup.$(date +%Y%m%d)" ]]; then
    cp "$BASHRC" "$BASHRC.backup.$(date +%Y%m%d)"
    echo "[+] Backed up $BASHRC"
fi

# Remove old pi/grok aliases/functions
sed -i '/# === PI_AGENT ===/,/# === END_PI_AGENT ===/d' "$BASHRC" 2>/dev/null || true
sed -i '/# === GROK ===/,/# === END_GROK ===/d' "$BASHRC" 2>/dev/null || true
sed -i '/alias pi=/d' "$BASHRC" 2>/dev/null || true
sed -i '/alias grok=/d' "$BASHRC" 2>/dev/null || true

# Add new modular section
cat >> "$BASHRC" << 'EOF'

# === PI_AGENT ===
# Use local fork instead of system install
export PI_AGENT_HOME="$HOME/projects/pi-agent"
export PATH="$PI_AGENT_HOME/bin:$PATH"

pi() {
    local pkg="${1:-coding-agent}"
    shift 2>/dev/null || true
    cd "$PI_AGENT_HOME/packages/$pkg" && \
        python3 -m coding_agent "$@"
}

pi-audit() {
    cd "$PI_AGENT_HOME" && \
        npm run check 2>/dev/null || \
        echo "[WARN] No npm check available"
}

pi-logs() {
    local session="${1:-$(ls -t $HOME/.pi/sessions/*.jsonl 2>/dev/null | head -1)}"
    [[ -f "$session" ]] && tail -50 "$session" || echo "No session found"
}
# === END_PI_AGENT ===

# === GROK ===
# Use local fork instead of system install
export GROK_HOME="$HOME/projects/grok"
export PATH="$GROK_HOME/bin:$PATH"

grok() {
    cd "$GROK_HOME" && ./run.sh "$@"
}
# === END_GROK ===

# === TAILSCALE HELPERS ===
alias ts-status='tailscale status'
alias ts-ip='tailscale ip -4'
alias ts-serve='tailscale serve status'
alias ts-funnel='tailscale funnel status'
# === END_TAILSCALE ===
EOF

echo "[+] Updated $BASHRC"
echo "[+] Run: source ~/.bashrc"
