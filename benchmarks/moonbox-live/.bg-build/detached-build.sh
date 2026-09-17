#!/bin/bash
set -euo pipefail
export PATH="/usr/bin:/usr/local/bin:/command:${PATH}"
export HOME=/root
export NODE_ENV=production

FRONTEND="/mnt/agents/output/triangle-access/src/frontend"
LOG="/mnt/agents/output/.bg-build/detached-build.log"
PIDFILE="/mnt/agents/output/.bg-build/build.pid"
STATUS="/mnt/agents/output/.bg-build/build.status"

echo "[$(date -Iseconds)] BUILD STARTED" > "$STATUS"
echo $$ > "$PIDFILE"

cd "$FRONTEND"
if [ -L node_modules ] && [ -e node_modules ]; then
    echo "[$(date -Iseconds)] node_modules symlink OK" >> "$LOG"
else
    echo "[$(date -Iseconds)] Fixing node_modules symlink..." >> "$LOG"
    rm -rf node_modules 2>/dev/null || true
    ln -s /root/triangle-nm/node_modules node_modules
fi

# Run build
node node_modules/.bin/next build >> "$LOG" 2>&1
EXIT=$?

if [ $EXIT -eq 0 ]; then
    echo "[$(date -Iseconds)] BUILD SUCCESS" > "$STATUS"
    echo "[$(date -Iseconds)] BUILD SUCCESS" >> "$LOG"

    # Auto-commit on success
    cd /mnt/agents/output/triangle-access
    git add -A
    git commit -m "auto: build success $(date -Iseconds)" >> "$LOG" 2>&1 || true
    git push origin master --force >> "$LOG" 2>&1 || true
else
    echo "[$(date -Iseconds)] BUILD FAILED: $EXIT" > "$STATUS"
    echo "[$(date -Iseconds)] BUILD FAILED: $EXIT" >> "$LOG"
fi

rm -f "$PIDFILE"
