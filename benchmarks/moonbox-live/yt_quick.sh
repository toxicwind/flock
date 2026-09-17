#!/bin/bash
# One-liner fix for yt-dlp 403 on macOS
yt-dlp --cookies-from-browser safari --extractor-args "youtube:player_client=web" --user-agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36" --no-check-certificates "$@"
