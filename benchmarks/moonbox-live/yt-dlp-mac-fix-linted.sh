#!/bin/bash
# =============================================================================
# YT-DLP MAC FIX — PO Token Provider Setup
# For: macOS 12+ (Monterey/Ventura/Sonoma/Sequoia)
# Handles: Apple Silicon (M1/M2/M3) AND Intel Macs
# Auto-installs: deno, yt-dlp via Homebrew if missing
# =============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error()   { echo "${RED}[ERROR]${NC} $*" >&2; }
success() { echo "${GREEN}[OK]${NC} $*"; }
warn()    { echo "${YELLOW}[WARN]${NC} $*"; }
info()    { echo "[INFO] $*"; }

# =============================================================================
# STEP 0: Detect Mac architecture and paths
# =============================================================================
info "Detecting system..."
ARCH="$(uname -m)"
MACOS_VER="$(sw_vers -productVersion 2>/dev/null || echo 'unknown')"
info "Architecture: $ARCH | macOS: $MACOS_VER"

if [ "$ARCH" = "arm64" ]; then
    HOMEBREW_PREFIX="/opt/homebrew"
else
    HOMEBREW_PREFIX="/usr/local"
fi
info "Homebrew prefix: $HOMEBREW_PREFIX"

# =============================================================================
# STEP 1: Verify dependencies (auto-install if missing)
# =============================================================================
info "Checking dependencies..."

MISSING_DEPS=()

# Check Deno
DENO_BIN=""
for path in "$HOMEBREW_PREFIX/bin/deno" "$HOME/.deno/bin/deno" "$(command -v deno 2>/dev/null || true)"; do
    if [ -x "$path" ]; then
        DENO_BIN="$path"
        break
    fi
done
[ -z "$DENO_BIN" ] && MISSING_DEPS+=("deno")

# Check yt-dlp
YTDLP_BIN=""
for path in "$HOMEBREW_PREFIX/bin/yt-dlp" "$(command -v yt-dlp 2>/dev/null || true)" "$HOME/.local/bin/yt-dlp"; do
    if [ -x "$path" ]; then
        YTDLP_BIN="$path"
        break
    fi
done
[ -z "$YTDLP_BIN" ] && MISSING_DEPS+=("yt-dlp")

# Auto-install missing deps
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    info "Auto-installing: ${MISSING_DEPS[*]}"

    BREW_BIN=""
    for path in "$HOMEBREW_PREFIX/bin/brew" "/usr/local/bin/brew"; do
        [ -x "$path" ] && BREW_BIN="$path" && break
    done

    if [ -z "$BREW_BIN" ]; then
        error "Homebrew not found. Install from https://brew.sh"
        exit 1
    fi

    "$BREW_BIN" update --quiet 2>/dev/null || true
    if "$BREW_BIN" install "${MISSING_DEPS[@]}" 2>&1; then
        success "Dependencies installed"
    else
        error "brew install failed"
        exit 1
    fi

    # Re-detect after install
    for path in "$HOMEBREW_PREFIX/bin/deno" "$HOME/.deno/bin/deno" "$(command -v deno 2>/dev/null || true)"; do
        [ -x "$path" ] && DENO_BIN="$path" && break
    done
    for path in "$HOMEBREW_PREFIX/bin/yt-dlp" "$(command -v yt-dlp 2>/dev/null || true)"; do
        [ -x "$path" ] && YTDLP_BIN="$path" && break
    done
fi

if [ -z "$DENO_BIN" ] || [ -z "$YTDLP_BIN" ]; then
    error "Dependencies still missing"
    exit 1
fi

success "Deno: $DENO_BIN"
success "yt-dlp: $YTDLP_BIN"

# =============================================================================
# STEP 2: Install PO Token Provider
# =============================================================================
info "Installing PO Token Provider..."
export PATH="$HOME/.deno/bin:$HOMEBREW_PREFIX/bin:$PATH"

DENO_INSTALL_OK=false
for attempt in 1 2 3; do
    if "$DENO_BIN" install -A -f -g -n yt-pot-provider jsr:@fsh/yt-pot-provider 2>/dev/null; then
        DENO_INSTALL_OK=true
        break
    fi
    warn "Install attempt $attempt failed, retrying..."
    sleep $((attempt * 2))
done

[ "$DENO_INSTALL_OK" = false ] && error "Failed to install PO Token Provider" && exit 1
success "PO Token Provider installed"

POT_BIN=""
for path in "$HOME/.deno/bin/yt-pot-provider" "$(command -v yt-pot-provider 2>/dev/null || true)"; do
    [ -x "$path" ] && POT_BIN="$path" && break
done
[ -z "$POT_BIN" ] && error "Provider binary not found" && exit 1
success "Provider binary: $POT_BIN"

# =============================================================================
# STEP 3: Create LaunchAgent plist
# =============================================================================
info "Creating LaunchAgent..."

LAUNCHDIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCHDIR/com.ytdlp.pot-provider.plist"
mkdir -p "$LAUNCHDIR"

DENO_ABS="$(cd "$(dirname "$DENO_BIN")" && pwd)/$(basename "$DENO_BIN")"

# Write plist with variable expansion
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ytdlp.pot-provider</string>
    <key>ProgramArguments</key>
    <array>
        <string>${DENO_ABS}</string>
        <string>run</string>
        <string>--allow-net</string>
        <string>--allow-read</string>
        <string>jsr:@fsh/yt-pot-provider</string>
        <string>--port</string>
        <string>4444</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardErrorPath</key>
    <string>/tmp/yt-pot-provider.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/yt-pot-provider.out</string>
    <key>WorkingDirectory</key>
    <string>/tmp</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>${HOMEBREW_PREFIX}/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

chmod 600 "$PLIST_PATH"
success "LaunchAgent created"

# =============================================================================
# STEP 4: Load LaunchAgent
# =============================================================================
info "Loading LaunchAgent..."
launchctl bootout "gui/$(id -u)/com.ytdlp.pot-provider" 2>/dev/null || true
launchctl unload "$PLIST_PATH" 2>/dev/null || true
sleep 1

if launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null; then
    success "LaunchAgent loaded"
elif launchctl load -w "$PLIST_PATH" 2>/dev/null; then
    success "LaunchAgent loaded (legacy)"
else
    warn "LaunchAgent load failed, starting manually..."
    nohup "$DENO_ABS" run --allow-net --allow-read jsr:@fsh/yt-pot-provider --port 4444 > /tmp/yt-pot-provider.out 2> /tmp/yt-pot-provider.err &
    sleep 2
fi

# =============================================================================
# STEP 5: Wait for provider
# =============================================================================
info "Waiting for provider..."
PROVIDER_READY=false
for i in {1..15}; do
    if curl -sf http://127.0.0.1:4444/health 2>/dev/null | grep -q "ok"; then
        PROVIDER_READY=true
        break
    fi
    sleep 1
done

[ "$PROVIDER_READY" = true ] && success "Provider ready on http://127.0.0.1:4444" || warn "Provider HTTP not responding yet"

# =============================================================================
# STEP 6: Write yt-dlp config
# =============================================================================
info "Writing yt-dlp config..."

CONFIGDIR="$HOME/.config/yt-dlp"
mkdir -p "$CONFIGDIR"

[ -f "$CONFIGDIR/config" ] && cp "$CONFIGDIR/config" "$CONFIGDIR/config.bak.$(date +%s)"

# Single-quoted heredoc = NO variable expansion, literal content
cat > "$CONFIGDIR/config" << 'CONFIG'
--extractor-args "youtube:player_client=web,ios,tv,web_creator;po_token_provider=http://127.0.0.1:4444"
--format-sort "res,fps,codec:h264:m4a,size"
-f "bestvideo[vcodec^=avc1][height<=1080]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
--merge-output-format mp4
--http-chunk-size 10M
--buffer-size 16K
--retries 10
--fragment-retries 10
--continue
--no-check-certificates
--paths "home:~/Downloads"
-o "%(title)s [%(id)s].%(ext)s"
--restrict-filenames
--no-warnings
--console-title
CONFIG

success "Config written: $CONFIGDIR/config"

# =============================================================================
# STEP 7: Test download
# =============================================================================
info "Testing download..."
TEST_URL="https://youtu.be/iQsu3Kz9NYo"

info "Testing iOS fallback..."
if "$YTDLP_BIN" --no-config --extractor-args "youtube:player_client=ios" \
    -f "best[height<=720]" --no-playlist -o "/tmp/yt-dlp-test.%(ext)s" \
    "$TEST_URL" 2>/tmp/yt-dlp-test.err; then

    success "iOS client works"
    rm -f /tmp/yt-dlp-test.*

    info "Testing with PO Token Provider..."
    if "$YTDLP_BIN" -f "best[height<=720]" --no-playlist -o "/tmp/yt-dlp-test2.%(ext)s" \
        "$TEST_URL" 2>/tmp/yt-dlp-test2.err; then
        success "Full pipeline operational"
        rm -f /tmp/yt-dlp-test2.*
    else
        warn "PO Token test failed, but iOS fallback works"
    fi
else
    error "All methods failed. Check /tmp/yt-dlp-test.err"
    echo "Try: brew upgrade yt-dlp"
    exit 1
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo "========================================================="
echo " SETUP COMPLETE"
echo "========================================================="
echo ""
echo "PO Token Provider: http://127.0.0.1:4444"
echo "Config:            ~/.config/yt-dlp/config"
echo "LaunchAgent:       ~/Library/LaunchAgents/com.ytdlp.pot-provider.plist"
echo "Logs:              /tmp/yt-pot-provider.{out,err}"
echo ""
echo "Usage: yt-dlp <URL>"
echo "========================================================="
