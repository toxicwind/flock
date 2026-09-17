#!/bin/bash
# Real-time terminal output capture via tee
# Usage: source this file, then all commands pipe through logger

LOGFILE="/mnt/agents/output/terminal_audit_$(date +%Y%m%d_%H%M%S).log"
export LOGFILE

# Function to wrap any command with logging
logcmd() {
    echo "=== $(date -Iseconds) CMD: $* ===" | tee -a "$LOGFILE"
    "$@" 2>&1 | tee -a "$LOGFILE"
    echo "=== EXIT: $? ===" | tee -a "$LOGFILE"
}

# Auto-log all shell output
exec > >(tee -a "$LOGFILE")
exec 2> >(tee -a "$LOGFILE" >&2)

echo "[HOOK ACTIVE] Logging to: $LOGFILE"
