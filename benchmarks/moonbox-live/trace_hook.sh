#!/bin/bash
# trace_hook.sh — ALWAYS capture full output, never truncate
# Usage: source /mnt/agents/output/trace_hook.sh
#        trace "your command here"
#        trace_file /path/to/large/file

TRACE_DIR="/mnt/agents/output/.bg_logs/traces"
mkdir -p "$TRACE_DIR"

trace() {
    local cmd="$1"
    local name="trace_$(date +%s)_$$
    local out="$TRACE_DIR/${name}.txt"
    echo "[TRACE] Running: $cmd" >&2
    echo "[TRACE] Output will be at: $out" >&2
    eval "$cmd" > "$out" 2>&1
    local size=$(wc -c < "$out")
    echo "[TRACE] Output size: $size bytes" >&2
    # Auto-chunk and output
    if [ "$size" -gt 8500 ]; then
        echo "[TRACE] CHUNKED OUTPUT (use trace_read $name to view)" >&2
    else
        cat "$out"
    fi
    echo "$out"
}

trace_read() {
    local name="$1"
    local part="${2:-0}"
    local out="$TRACE_DIR/${name}.txt"
    [ ! -f "$out" ] && echo "[TRACE] Not found: $out" >&2 && return 1
    local size=$(wc -c < "$out")
    local offset=$((part * 8500))
    if [ "$offset" -ge "$size" ]; then
        echo "[TRACE] Part $part beyond file size ($size)" >&2
        return 1
    fi
    echo "[TRACE] $name | part $part | offset $offset | total $size"
    tail -c +$((offset + 1)) "$out" | head -c 8500
}

trace_list() {
    ls -lt "$TRACE_DIR" | head -20
}

trace_file() {
    local file="$1"
    local size=$(wc -c < "$file")
    echo "[TRACE] File: $file | Size: $size bytes"
    if [ "$size" -gt 8500 ]; then
        local parts=$(( (size + 8499) / 8500 ))
        echo "[TRACE] Use: trace_file_part $file <0-$((parts-1))>"
    else
        cat "$file"
    fi
}

trace_file_part() {
    local file="$1"
    local part="${2:-0}"
    local size=$(wc -c < "$file")
    local offset=$((part * 8500))
    tail -c +$((offset + 1)) "$file" | head -c 8500
}
