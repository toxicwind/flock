#!/bin/bash
# =============================================================================
# YT-DLP macOS 403 Forbidden Fix — Multi-tier fallback
# =============================================================================
set -euo pipefail

VIDEO_URL="${1:-}"
if [[ -z "$VIDEO_URL" ]]; then
    echo "Usage: $0 <youtube-url> [output-dir]"
    echo ""
    echo "Examples:"
    echo "  $0 'https://youtu.be/iQsu3Kz9NYo'"
    echo "  $0 'https://www.youtube.com/watch?v=iQsu3Kz9NYo' ~/Downloads"
    exit 1
fi

OUTDIR="${2:-$HOME/Downloads}"
mkdir -p "$OUTDIR"

# Detect browser for cookie extraction
BROWSER=""
for b in safari chrome firefox edge; do
    if command -v "$b" >/dev/null 2>&1 || [[ -d "$HOME/Library/Application Support/$b" ]] 2>/dev/null; then
        BROWSER="$b"
        break
    fi
done
[[ -z "$BROWSER" ]] && BROWSER="safari"

echo "[*] Target: $VIDEO_URL"
echo "[*] Output: $OUTDIR"
echo "[*] Browser for cookies: $BROWSER"

# Build yt-dlp command with progressive fallbacks
YT_DLP="$(command -v yt-dlp || echo '/usr/local/bin/yt-dlp')"

# Tier 1: Cookies from browser + web client + PO token attempt
echo ""
echo "=== TIER 1: Browser cookies + web client ==="
$YT_DLP \
    --cookies-from-browser "$BROWSER" \
    --extractor-args "youtube:player_client=web" \
    --extractor-args "youtube:player_skip=webpage,configs,js" \
    --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
    --referer "https://www.youtube.com/" \
    --add-header "Accept-Language:en-US,en;q=0.9" \
    --no-check-certificates \
    --no-warnings \
    -o "$OUTDIR/%(title)s.%(ext)s" \
    "$VIDEO_URL" 2>&1 && {
        echo "[OK] Tier 1 succeeded"
        exit 0
    }

# Tier 2: Try with just cookies, no PO token
echo ""
echo "=== TIER 2: Cookies only (no PO token) ==="
$YT_DLP \
    --cookies-from-browser "$BROWSER" \
    --extractor-args "youtube:player_client=web" \
    --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15" \
    --no-check-certificates \
    --no-warnings \
    -o "$OUTDIR/%(title)s.%(ext)s" \
    "$VIDEO_URL" 2>&1 && {
        echo "[OK] Tier 2 succeeded"
        exit 0
    }

# Tier 3: No cookies, just impersonate web client
echo ""
echo "=== TIER 3: Impersonate web client (no cookies) ==="
$YT_DLP \
    --extractor-args "youtube:player_client=web" \
    --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
    --referer "https://www.youtube.com/" \
    --no-check-certificates \
    --no-warnings \
    -o "$OUTDIR/%(title)s.%(ext)s" \
    "$VIDEO_URL" 2>&1 && {
        echo "[OK] Tier 3 succeeded"
        exit 0
    }

# Tier 4: Force specific format, bypass age-gate
echo ""
echo "=== TIER 4: Force format + age-gate bypass ==="
$YT_DLP \
    --extractor-args "youtube:player_client=web" \
    --extractor-args "youtube:player_skip=webpage,configs,js" \
    --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
    --no-check-certificates \
    --no-warnings \
    --yes-playlist \
    -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" \
    -o "$OUTDIR/%(title)s.%(ext)s" \
    "$VIDEO_URL" 2>&1 && {
        echo "[OK] Tier 4 succeeded"
        exit 0
    }

# Tier 5: Nuclear option — extract audio only
echo ""
echo "=== TIER 5: Audio-only fallback ==="
$YT_DLP \
    --extractor-args "youtube:player_client=web" \
    --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" \
    --no-check-certificates \
    --no-warnings \
    -x --audio-format mp3 \
    -o "$OUTDIR/%(title)s.%(ext)s" \
    "$VIDEO_URL" 2>&1 && {
        echo "[OK] Tier 5 succeeded (audio only)"
        exit 0
    }

echo ""
echo "[FATAL] All tiers failed. YouTube may have blocked this IP or the video is region-restricted."
echo ""
echo "Try:"
echo "  1. Use a VPN or different network"
echo "  2. Update yt-dlp: yt-dlp -U"
echo "  3. Try with --verbose for detailed error info"
exit 1
