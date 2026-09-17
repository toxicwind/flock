#!/bin/bash
# 28s hard kill v2 — uses timeout command + setsid for true isolation
set -euo pipefail
CMD="$*"
LOG="/mnt/agents/output/.dssh_logs/kill28_v2_$$.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date +%s.%N)] START pid=$$ cmd='$CMD'" >> "$LOG"

# Use setsid to create new session, timeout to hard kill
# timeout -s9 = SIGKILL after 28s
setsid timeout -s9 28 bash -c "$CMD" 2>>"$LOG" &
CHILD=$!
echo "[$(date +%s.%N)] CHILD=$CHILD" >> "$LOG"

wait "$CHILD" 2>/dev/null
EXIT=$?
echo "[$(date +%s.%N)] EXIT=$EXIT" >> "$LOG"
exit $EXIT
