#!/bin/bash
# Rapid curl tar.gz clone with PAT — NO GIT BINARY INVOKED
set -euo pipefail
PAT="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"
DEST="/mnt/agents/output/repos_$(date +%s)"
mkdir -p "$DEST"
LOG="/mnt/agents/output/.dssh_logs/rapid_clone_$(date +%s).log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date +%s.%N)] START" >> "$LOG"

# Repo 1: effusion-labs
echo "[$(date +%s.%N)] CLONE effusion-labs" >> "$LOG"
curl -sL -H "Authorization: token $PAT" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/effusion-labs/effusion-labs/tarball/main" -o "$DEST/effusion-labs.tar.gz" 2>>"$LOG" && \
tar -xzf "$DEST/effusion-labs.tar.gz" -C "$DEST" --strip-components=1 2>>"$LOG" && \
echo "[$(date +%s.%N)] effusion-labs OK" >> "$LOG" || echo "[$(date +%s.%N)] effusion-labs FAIL" >> "$LOG"

# Repo 2: envd-project  
echo "[$(date +%s.%N)] CLONE envd-project" >> "$LOG"
curl -sL -H "Authorization: token $PAT" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/envd-project/envd/tarball/main" -o "$DEST/envd.tar.gz" 2>>"$LOG" && \
tar -xzf "$DEST/envd.tar.gz" -C "$DEST/envd" --strip-components=1 2>>"$LOG" && \
echo "[$(date +%s.%N)] envd OK" >> "$LOG" || echo "[$(date +%s.%N)] envd FAIL" >> "$LOG"

# Repo 3: triangle-access
echo "[$(date +%s.%N)] CLONE triangle-access" >> "$LOG"
curl -sL -H "Authorization: token $PAT" -H "Accept: application/vnd.github.v3+json" "https://api.github.com/repos/triangle-access/triangle-access/tarball/main" -o "$DEST/triangle.tar.gz" 2>>"$LOG" && \
tar -xzf "$DEST/triangle.tar.gz" -C "$DEST/triangle" --strip-components=1 2>>"$LOG" && \
echo "[$(date +%s.%N)] triangle OK" >> "$LOG" || echo "[$(date +%s.%N)] triangle FAIL" >> "$LOG"

echo "[$(date +%s.%N)] DONE" >> "$LOG"
ls -la "$DEST" >> "$LOG" 2>&1
