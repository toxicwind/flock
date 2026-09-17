#!/bin/bash
# bg.sh — Background worker management

BG_DAEMON="/mnt/agents/output/.bg_daemon.sh"

tmux_start() {
    tmux has-session -t toxicwind 2>/dev/null || {
        tmux new-session -d -s toxicwind -n main "bash -c \"cd /mnt/agents/output/toxicwind-repos && exec bash\""
        tmux new-window -t toxicwind -n zmq "bash -c \"cd /mnt/agents/output && exec bash\""
        tmux new-window -t toxicwind -n audit "bash -c \"cd /mnt/agents/output && exec bash\""
    }
}

tmux_attach() {
    tmux attach -t toxicwind
}

tmux_kill() {
    tmux kill-session -t toxicwind 2>/dev/null || true
}

daemon_start() {
    local name="$1"
    local cmd="$2"
    bash "$BG_DAEMON" start "$name" "$cmd"
}

daemon_status() {
    bash "$BG_DAEMON" status
}

daemon_stop() {
    bash "$BG_DAEMON" stop "$1"
}
