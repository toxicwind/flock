#!/bin/bash
set -euo pipefail

echo "==> [1/4] Installing local BotGuard PO Token Provider via Deno..."
DENO_BIN="$(command -v deno || echo "/opt/homebrew/bin/deno")"

if [ ! -x "$DENO_BIN" ]; then
  echo "Error: Deno binary not found. Run 'brew install deno' first."
  exit 1
fi

"$DENO_BIN" install -A -f -g -n yt-pot-provider jsr:@fsh/yt-pot-provider

# Resolve path to installed provider binary
POT_BIN="$(command -v yt-pot-provider || echo "$HOME/.deno/bin/yt-pot-provider")"

echo "==> [2/4] Registering persistent background LaunchAgent..."
mkdir -p "$HOME/Library/LaunchAgents"

cat << PLIST > "$HOME/Library/LaunchAgents/com.ytdlp.pot-provider.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ytdlp.pot-provider</string>
    <key>ProgramArguments</key>
    <array>
        <string>${DENO_BIN}</string>
        <string>run</string>
        <string>-A</string>
        <string>jsr:@fsh/yt-pot-provider</string>
        <string>--port</string>
        <string>4444</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>/tmp/yt-pot-provider.err</string>
    <key>StandardOutPath</key>
    <string>/tmp/yt-pot-provider.out</string>
</dict>
</plist>
PLIST

# Unload previous instance if exists, then load new service
launchctl bootout "gui/$(id -u)/com.ytdlp.pot-provider" 2>/dev/null || launchctl unload "$HOME/Library/LaunchAgents/com.ytdlp.pot-provider.plist" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.ytdlp.pot-provider.plist" 2>/dev/null || launchctl load -w "$HOME/Library/LaunchAgents/com.ytdlp.pot-provider.plist"

sleep 1

echo "==> [3/4] Writing permanent yt-dlp config..."
mkdir -p "$HOME/.config/yt-dlp"

cat << 'CONFIG' > "$HOME/.config/yt-dlp/config"
# Hook into background PO Token Provider & mobile fallback cascade
--extractor-args "youtube:player_client=web,ios,tv,web_creator;po_token_provider=http://127.0.0.1:4444"

# Standard Mac MP4 container sorting (H.264/AAC preferred for QuickTime)
--format-sort "res,fps,codec:h264:m4a,size"
-f "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best"
--merge-output-format mp4

# Stream stability & GVS chunk limits
--http-chunk-size 10M
--retries 10
--fragment-retries 10
--continue

# Output folder
--paths "home:~/Downloads"
-o "%(title)s [%(id)s].%(ext)s"
CONFIG

echo "==> [4/4] Verifying pipeline with test download..."
yt-dlp "https://youtu.be/iQsu3Kz9NYo"

echo ""
echo "========================================================="
echo " SETUP COMPLETE: Background PO Token service is active."
echo " Videos will download to ~/Downloads automatically."
echo " Usage: yt-dlp <URL>"
echo "========================================================="
