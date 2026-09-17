#!/usr/bin/env bash
# Auto-init git for /mnt/agents/dot — never manually reinit again
set -euo pipefail

dot="/mnt/agents/dot"
cd "$dot"

# If _git exists but .git doesnt, link it
if [ -d "_git" ] && [ ! -e ".git" ]; then
    echo "gitdir: $dot/_git" > .git
    git --git-dir="$dot/_git" config --bool core.bare false 2>/dev/null || true
    git --git-dir="$dot/_git" config core.worktree "$dot" 2>/dev/null || true
    echo "[+] Linked _git -> .git"
fi

# If neither exists, init fresh
if [ ! -d ".git" ] && [ ! -d "_git" ]; then
    git init
    git config user.email "auto@kimi.local"
    git config user.name "Auto Init"
    echo "[+] Fresh git init"
fi

# Ensure readable
chmod -R +r .git 2>/dev/null || chmod -R +r _git 2>/dev/null || true

echo "[+] Git ready: $(git rev-parse --git-dir 2>/dev/null || echo unknown)"
echo "[+] Branch: $(git branch --show-current 2>/dev/null || echo none)"
