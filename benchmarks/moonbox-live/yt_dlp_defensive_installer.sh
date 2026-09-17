#!/bin/bash
# =============================================================================
# YT-DLP AUGUST 2026 FIX — Defensive Dynamic Installer
# Handles existing aliases, functions, plugins, and conflicting configs
# =============================================================================
set -euo pipefail

ZSHRC="${HOME}/.zshrc"
BACKUP="${ZSHRC}.bak.ytdlp-fix.$(date +%s)"
MARKER="# === YT-DLP-AUG-2026-FIX-BEGIN ==="
MARKER_END="# === YT-DLP-AUG-2026-FIX-END ==="

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*"; }

# =============================================================================
# 1. DETECT EXISTING YT-DLP CONFIG
# =============================================================================
info "Scanning existing shell config..."

# Check for existing yt-dlp function
HAS_FUNC=$(grep -c 'yt-dlp()' "$ZSHRC" 2>/dev/null || echo 0)
HAS_ALIAS=$(grep -c 'alias yt-dlp' "$ZSHRC" 2>/dev/null || echo 0)
HAS_MARKER=$(grep -c "$MARKER" "$ZSHRC" 2>/dev/null || echo 0)
HAS_PLUGINS=$(ls -d ~/.config/yt-dlp/plugins/*/ 2>/dev/null | wc -l)

info "Found: ${HAS_FUNC} functions, ${HAS_ALIAS} aliases, ${HAS_MARKER} previous installs, ${HAS_PLUGINS} plugins"

# =============================================================================
# 2. BACKUP ZSHRC
# =============================================================================
cp "$ZSHRC" "$BACKUP"
info "Backed up .zshrc to ${BACKUP}"

# =============================================================================
# 3. REMOVE PREVIOUS INSTALL (idempotent)
# =============================================================================
if [[ "$HAS_MARKER" -gt 0 ]]; then
    warn "Removing previous yt-dlp fix from .zshrc..."
    # Remove between markers
    awk -v m="$MARKER" -v e="$MARKER_END" '
        $0 ~ m { skip=1; next }
        $0 ~ e { skip=0; next }
        !skip { print }
    ' "$ZSHRC" > "${ZSHRC}.tmp" && mv "${ZSHRC}.tmp" "$ZSHRC"
fi

# =============================================================================
# 4. CHECK FOR CONFLICTING ALIASES/FUNCTIONS
# =============================================================================
if [[ "$HAS_FUNC" -gt 0 && "$HAS_MARKER" -eq 0 ]]; then
    warn "Existing yt-dlp() function detected in .zshrc"
    warn "This installer will create 'ytdlp' instead of overriding 'yt-dlp'"
    FUNC_NAME="ytdlp"
else
    FUNC_NAME="yt-dlp"
fi

if [[ "$HAS_ALIAS" -gt 0 && "$HAS_MARKER" -eq 0 ]]; then
    warn "Existing 'alias yt-dlp' detected"
    warn "Commenting out old alias..."
    sed -i.bak 's/^alias yt-dlp=/# &/' "$ZSHRC" 2>/dev/null || true
fi

# =============================================================================
# 5. INSTALL DEPS (Deno + bgutil plugin)
# =============================================================================
info "Installing Deno..."
if ! command -v deno >/dev/null 2>&1; then
    curl -fsSL https://deno.land/install.sh | sh 2>/dev/null || {
        err "Deno install failed. Install manually: https://deno.land"
        exit 1
    }
    export PATH="$HOME/.deno/bin:$PATH"
fi
info "Deno: $(deno --version 2>/dev/null | head -1)"

info "Installing bgutil PO token provider..."
mkdir -p ~/.config/yt-dlp/plugins
rm -rf ~/.config/yt-dlp/plugins/bgutil-ytdlp-pot-provider
TMPDIR=$(mktemp -d)
curl -fsSL --max-time 30 \
    "https://github.com/Brainicism/bgutil-ytdlp-pot-provider/archive/refs/heads/main.tar.gz" \
    -o "${TMPDIR}/bgutil.tar.gz" 2>/dev/null && \
    tar -xzf "${TMPDIR}/bgutil.tar.gz" -C ~/.config/yt-dlp/plugins/ 2>/dev/null && \
    mv ~/.config/yt-dlp/plugins/bgutil-ytdlp-pot-provider-main \
       ~/.config/yt-dlp/plugins/bgutil-ytdlp-pot-provider 2>/dev/null || {
    err "Plugin install failed"
    rm -rf "$TMPDIR"
    exit 1
}
rm -rf "$TMPDIR"
info "Plugin installed"

# =============================================================================
# 6. UPDATE YT-DLP TO NIGHTLY
# =============================================================================
info "Updating yt-dlp to nightly..."
if command -v yt-dlp >/dev/null 2>&1; then
    yt-dlp --update-to nightly 2>/dev/null || warn "yt-dlp update failed (may need manual update)"
else
    warn "yt-dlp not found in PATH. Install with: brew install yt-dlp"
fi

# =============================================================================
# 7. INJECT DYNAMIC WRAPPER INTO ZSHRC
# =============================================================================
info "Injecting dynamic wrapper into .zshrc..."

cat >> "$ZSHRC" << BLOCK

${MARKER}
# Auto-installed: $(date -Iseconds)
# This block is managed by the yt-dlp Aug 2026 fix installer.
# To remove: run the installer again (it's idempotent) or delete between markers.

# Ensure Deno is in PATH for the PO token provider
export PATH="\$HOME/.deno/bin:\$PATH" 2>/dev/null || true

# Dynamic yt-dlp wrapper: auto-detects browser, generates PO tokens per-video
${FUNC_NAME}() {
    local BROWSER=""
    local BROWSER_DIRS=("Safari" "Google/Chrome" "Firefox" "Microsoft Edge" "BraveSoftware/Brave-Browser")
    local BROWSER_NAMES=(safari chrome firefox edge brave)

    # Detect which browser has YouTube cookies
    for i in "\${!BROWSER_DIRS[@]}"; do
        local dir="\${HOME}/Library/Application Support/\${BROWSER_DIRS[$i]}"
        if [[ -d "\$dir" ]] 2>/dev/null; then
            BROWSER="\${BROWSER_NAMES[$i]}"
            break
        fi
    done

    # Build args dynamically
    local ARGS=(
        --extractor-args "youtube:player_client=web"
        --extractor-args "youtube:po_token=bgutil"
        --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        --no-check-certificates
        -f "best"
    )

    # Add cookies if browser detected
    if [[ -n "\$BROWSER" ]]; then
        ARGS+=(--cookies-from-browser "\$BROWSER")
    fi

    # Forward all user args
    command yt-dlp "\${ARGS[@]}" "\$@"
}

${MARKER_END}
BLOCK

info "Wrapper injected as '${FUNC_NAME}'"

# =============================================================================
# 8. SOURCE AND VERIFY
# =============================================================================
source "$ZSHRC" 2>/dev/null || warn "Could not source .zshrc (run 'source ~/.zshrc' manually)"

info ""
info "=== INSTALL COMPLETE ==="
info "Command: ${FUNC_NAME} <url>"
info ""
info "To verify: ${FUNC_NAME} --version"
info "To test:   ${FUNC_NAME} 'https://youtu.be/iQsu3Kz9NYo'"
info ""
info "If broken, restore backup: cp ${BACKUP} ~/.zshrc"
