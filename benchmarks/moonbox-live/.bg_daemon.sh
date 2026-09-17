#!/bin/bash
# BG Daemon v3 — Timeout backgrounds instead of killing
set -uo pipefail
PID_DIR="/mnt/agents/output/.bg_pids"
LOG_DIR="/mnt/agents/output/.unlimited_logs"
STATE_DIR="/mnt/agents/output/.bg_state"
mkdir -p "$PID_DIR" "$LOG_DIR" "$STATE_DIR"
_verify_pid() {
    local pid="$1" name="$2"
    [ -z "$pid" ] && return 1
    [ ! -d "/proc/$pid" ] && return 1
    tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "$name"
}
case "$1" in
  start)
    NAME="$2"; shift 2; CMD="$@"
    LOG="$LOG_DIR/${NAME}.log"
    PIDFILE="$PID_DIR/${NAME}.pid"
    STATEFILE="$STATE_DIR/${NAME}.json"
    if [ -f "$PIDFILE" ]; then
      OLD_PID=$(cat "$PIDFILE" 2>/dev/null)
      if _verify_pid "$OLD_PID" "$NAME"; then
        kill -TERM "$OLD_PID" 2>/dev/null
        sleep 2
        kill -0 "$OLD_PID" 2>/dev/null && kill -9 "$OLD_PID" 2>/dev/null
      fi
      rm -f "$PIDFILE"
    fi
    nohup bash -c "$CMD" >> "$LOG" 2>&1 &
    LAUNCHER_PID=$!
    echo "$LAUNCHER_PID" > "$PIDFILE"
    echo "{\"status\":\"started\",\"pid\":$LAUNCHER_PID,\"started_at\":$(date +%s)}" > "$STATEFILE"
    echo "[BG] Started $NAME (PID: $LAUNCHER_PID, backgrounds on timeout)"
    ;;
  status)
    for pidfile in "$PID_DIR"/*.pid; do
      [ -f "$pidfile" ] || continue
      name=$(basename "$pidfile" .pid)
      pid=$(cat "$pidfile" 2>/dev/null)
      _verify_pid "$pid" "$name" && echo "[BG] $name: RUNNING (PID: $pid)" || echo "[BG] $name: DEAD (stale)"
    done
    ;;
  stop)
    NAME="$2"
    PIDFILE="$PID_DIR/${NAME}.pid"
    if [ -f "$PIDFILE" ]; then
      PID=$(cat "$PIDFILE" 2>/dev/null)
      [ -n "$PID" ] && { kill -TERM "$PID" 2>/dev/null; sleep 2; kill -0 "$PID" 2>/dev/null && kill -9 "$PID" 2>/dev/null; }
      rm -f "$PIDFILE"
    fi
    echo "[BG] Stopped $NAME"
    ;;
  *) echo "Usage: $0 start <name> <cmd> | status | stop <name>" ;;
esac
