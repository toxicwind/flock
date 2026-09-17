#!/usr/bin/env bash
# apply-pi-fork.sh — Run this on awrawr-pc to replace system pi with local fork
set -euo pipefail

PI_FORK=/home/toxic/projects/pi-agent
PI_PACKAGE=${PI_FORK}/packages/coding-agent
BIN_DIR=$HOME/bin

mkdir -p $BIN_DIR

# 1. Build the fork if needed
echo '[1/5] Building pi-agent fork...'
cd $PI_FORK || { echo "Fork not found at $PI_FORK"; exit 1; }

if [[ ! -d ${PI_PACKAGE}/dist ]]; then
    npm run build --workspace=packages/coding-agent 2>/dev/null || npm run build
fi

# 2. Install pi wrapper
echo '[2/5] Installing pi wrapper...'
cat > $BIN_DIR/pi << 'WRAPPER'
#!/usr/bin/env bash
PI_FORK=/home/toxic/projects/pi-agent
PI_PACKAGE=${PI_FORK}/packages/coding-agent
if [[ ! -f ${PI_PACKAGE}/dist/cli.js ]]; then
    echo '[pi] Building...' >&2
    (cd $PI_FORK && npm run build --workspace=packages/coding-agent 2>/dev/null || npm run build)
fi
exec node ${PI_PACKAGE}/dist/cli.js "$@"
WRAPPER
chmod +x $BIN_DIR/pi

# 3. Install grok stub
echo '[3/5] Installing grok wrapper...'
cat > $BIN_DIR/grok << 'WRAPPER'
#!/usr/bin/env bash
GROK_FORK=/home/toxic/projects/grok
if [[ ! -d $GROK_FORK ]]; then
    echo '[grok] Fork not cloned. Run: git clone <your-fork> $GROK_FORK' >&2
    exit 1
fi
# TODO: Add grok build/run logic
exec echo '[grok] Ready — add your run logic to $0'
WRAPPER
chmod +x $BIN_DIR/grok

# 4. Patch .bashrc (idempotent)
echo '[4/5] Patching .bashrc...'
if ! grep -q 'PI FORK OVERRIDES' $HOME/.bashrc 2>/dev/null; then
    cat >> $HOME/.bashrc << 'EOF'

# === PI FORK OVERRIDES ===
export PATH=$HOME/bin:$PATH
export PATH=/home/toxic/projects/pi-agent/node_modules/.bin:$PATH
alias cdp='cd /home/toxic/projects/pi-agent'
alias cdg='cd /home/toxic/projects/grok 2>/dev/null || echo grok not cloned'
alias ts='tailscale'
# === END PI FORK OVERRIDES ===
EOF
    echo '[✓] .bashrc patched'
else
    echo '[✓] .bashrc already patched'
fi

# 5. Handle untracked TUI files
echo '[5/5] Checking untracked TUI files...'
cd $PI_FORK
if git status --short packages/tui/src/ 2>/dev/null | grep -q '^??'; then
    echo '[!] Untracked files found in packages/tui/src/:'
    git status --short packages/tui/src
    echo ''
    echo 'Decision needed:'
    echo 'A) git add packages/tui/src/  → Track as new features'
    echo 'B) echo "packages/tui/src/*.ts" >> .gitignore  → Ignore generated files'
    echo 'C) git stash push packages/tui/src/  → Stash for later'
fi

# 6. Verify
echo ''
echo '[✓] Installation complete!'
echo "  which pi  → $(which pi 2>/dev/null || echo 'not in PATH yet — run: source ~/.bashrc')"
echo '  pi --version output:'
pi --version 2>/dev/null || echo "  (build may be needed — run: cd $PI_FORK && npm run build)"
