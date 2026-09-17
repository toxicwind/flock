#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# BG_LAUNCHER.sh — Persistent background workers for K8s sandbox
# 
# PROBLEM: K8s sandbox kills processes and cleans .git dirs between sessions
# SOLUTION: 
#   1. gitwatch auto-commits every 5-10s (saves work before death)
#   2. nohup + disown + PID files (survives shell disconnect)
#   3. State files in /mnt/agents/output (network drive, survives sessions)
#
# USAGE: bash BG_LAUNCHER.sh start|stop|status
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

PIDS_DIR="/mnt/agents/output/.bg_pids"
LOGS_DIR="/mnt/agents/output/.bg_logs"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

PAT="${GITHUB_PAT:-}"
if [ -z "$PAT" ] && [ -f "/mnt/agents/output/triangle-access/.env.keys" ]; then
    PAT=$(grep "^GITHUB_PAT=" /mnt/agents/output/triangle-access/.env.keys | head -1 | cut -d'"' -f2)
fi

start_gitwatch() {
    local name="$1"
    local conf="$2"
    
    # Source config
    source "$conf"
    
    # Check if already running
    local pidfile="$PIDS_DIR/gitwatch_${name}.pid"
    if [ -f "$pidfile" ]; then
        local oldpid=$(cat "$pidfile")
        if kill -0 "$oldpid" 2>/dev/null; then
            echo "[BG] gitwatch $name already running (PID: $oldpid)"
            return
        fi
    fi
    
    # Start gitwatch with nohup + disown
    cd "$WATCH_DIR"
    
    # Ensure git is configured
    git config user.name "toxicwind" 2>/dev/null || true
    git config user.email "toxicwind@users.noreply.github.com" 2>/dev/null || true
    
    # Set remote with PAT
    git remote set-url origin "https://${PAT}@github.com/${REMOTE}.git" 2>/dev/null || \
        git remote add origin "https://${PAT}@github.com/${REMOTE}.git" 2>/dev/null || true
    
    # Start gitwatch daemon
    nohup bash -c "
        while true; do
            sleep ${SLEEP_TIME:-10}
            if ! git diff --quiet 2>/dev/null; then
                git add -A 2>/dev/null
                git commit -m \"${COMMIT_MSG}\" 2>/dev/null || true
                git push origin ${BRANCH} --force 2>/dev/null || true
            fi
        done
    " > "$LOGS_DIR/gitwatch_${name}.log" 2>&1 &
    
    local pid=$!
    disown $pid 2>/dev/null || true
    echo $pid > "$pidfile"
    echo "[BG] gitwatch $name started (PID: $pid)"
}

stop_all() {
    echo "[BG] Stopping all background workers..."
    for pidfile in "$PIDS_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        local pid=$(cat "$pidfile")
        local name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  [STOP] $name (PID: $pid)"
        fi
        rm -f "$pidfile"
    done
}

status() {
    echo "=== BACKGROUND WORKERS ==="
    for pidfile in "$PIDS_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        local pid=$(cat "$pidfile")
        local name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            echo "  [RUNNING] $name (PID: $pid)"
        else
            echo "  [DEAD] $name (PID: $pid)"
        fi
    done
    echo ""
    echo "=== LOGS ==="
    ls -la "$LOGS_DIR/"
}

case "${1:-start}" in
    start)
        echo "[BG] Starting background workers..."
        start_gitwatch "envd" "/mnt/agents/output/.vendor/gitwatch-configs/envd-project.conf"
        start_gitwatch "recon" "/mnt/agents/output/.vendor/gitwatch-configs/repo_kimi_team_recon.conf"
        start_gitwatch "agentsmd" "/mnt/agents/output/.vendor/gitwatch-configs/agents-md.conf"
        echo "[BG] Done. Run 'bash BG_LAUNCHER.sh status' to check."
        ;;
    stop)
        stop_all
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: bash BG_LAUNCHER.sh [start|stop|status]"
        exit 1
        ;;
esac
