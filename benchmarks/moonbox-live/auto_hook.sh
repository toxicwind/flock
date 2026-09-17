#!/bin/bash
# Auto-hook system v3 - works with both shell and python

HOOK_DIR="/mnt/agents/output/hooks"
LOG_DIR="/mnt/agents/output/hook_logs"
mkdir -p "$HOOK_DIR" "$LOG_DIR"

# Hook: on_file_created - triggers when new files appear in watched dirs
watch_and_trigger() {
    local watch_dir=$1
    local hook_name=$2
    local action=$3
    
    inotifywait -m -e create "$watch_dir" --format '%f' 2>/dev/null | while read file; do
        echo "$(date -Iseconds) TRIGGER $hook_name: $file" >> "$LOG_DIR/hook.log"
        eval "$action" >> "$LOG_DIR/${hook_name}.log" 2>&1
    done
}

# Hook: on_tool_limit - triggers background process when limit approaches
limit_escape() {
    local cmd="$1"
    local output="$2"
    nohup bash -c "$cmd; echo DONE > $output.done" > "$output.log" 2>&1 &
    echo $! > "$output.pid"
    echo "$(date -Iseconds) ESCAPE pid=$! output=$output" >> "$LOG_DIR/escape.log"
}

# Hook: git_auto_commit - auto commits when files change
auto_git() {
    local repo_dir="$1"
    cd "$repo_dir" || return
    git add -A
    git diff --cached --quiet || git commit -m "auto: $(date -Iseconds)"
}

echo "Auto-hook system loaded. Hooks: $(ls "$HOOK_DIR" 2>/dev/null | wc -l)"
