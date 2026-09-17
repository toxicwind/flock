#!/bin/bash
# 28s hard kill wrapper — bruteforce reliable
set -euo pipefail
CMD="$*"
PIDFILE="/tmp/kill28_$$.pid"
LOG="/mnt/agents/output/.dssh_logs/kill28_$$.log"
mkdir -p "$(dirname "$LOG")"

echo "[$(date +%s.%N)] START pid=$$ cmd='$CMD'" >> "$LOG"

# Spawn the real command in a subshell that we can kill-tree
(
  echo $$ > "$PIDFILE"
  exec bash -c "$CMD"
) &
CHILD=$!
echo "[$(date +%s.%N)] CHILD=$CHILD" >> "$LOG"

# Background killer: after 28s, SIGKILL the entire process group
(
  sleep 28
  if kill -0 "$CHILD" 2>/dev/null; then
    echo "[$(date +%s.%N)] KILLING pgid=$(ps -o pgid= "$CHILD" | tr -d ' ')" >> "$LOG"
    kill -9 -- -"$(ps -o pgid= "$CHILD" | tr -d ' ')" 2>/dev/null || kill -9 "$CHILD" 2>/dev/null
    echo "[$(date +%s.%N)] KILLED" >> "$LOG"
  fi
) &
KILLER=$!

wait "$CHILD" 2>/dev/null
EXIT=$?
echo "[$(date +%s.%N)] CHILD_EXIT=$EXIT" >> "$LOG"
kill "$KILLER" 2>/dev/null
rm -f "$PIDFILE"
exit $EXIT
