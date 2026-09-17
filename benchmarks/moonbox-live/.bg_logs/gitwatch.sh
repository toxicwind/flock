#!/bin/bash
# Git watcher — detached, nohup, survives parent death
LOGDIR="/mnt/agents/output/.bg_logs"
mkdir -p "$LOGDIR"
while true; do
  cd /mnt/agents/output/effusion-labs 2>/dev/null || continue
  git status --short > "$LOGDIR/gitwatch_status.log" 2>&1
  git log --oneline -5 >> "$LOGDIR/gitwatch_status.log" 2>&1
  sleep 30
done
