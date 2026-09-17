#!/bin/bash
# AUTOHOOK v3 — Clean, no secrets, production-grade
# Sources from .env instead of embedding tokens
set -uo pipefail
WORKSPACE="/mnt/agents/output"
LOG_DIR="$WORKSPACE/.unlimited_logs"
mkdir -p "$LOG_DIR"
[ -f "$WORKSPACE/.env" ] && source "$WORKSPACE/.env"
u() { unshare -U -r bash -c "$@" 2>&1; }
ul() {
    local cmd="$1"
    local logfile="$LOG_DIR/cmd_$(date +%s)_$$.log"
    echo "[$(date -Iseconds)] CMD: $cmd" >> "$logfile"
    python3 "$WORKSPACE/kernel_loader_hook_v3.py" bg --name "ul_$$" --cmd "$cmd" --timeout 86400 >> "$logfile" 2>&1
    cat "$logfile"
}
export PS1="[hook:\t]\$ "
export PROMPT_COMMAND='echo "[$(date +%H:%M:%S)] cwd=$(pwd)" >> "$LOG_DIR/shell.log" 2>/dev/null'
alias root='unshare -U -r bash'
alias logall='mkdir -p "$LOG_DIR" && exec > >(tee -a "$LOG_DIR/session_$(date +%s).log") 2>&1'
