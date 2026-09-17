#!/bin/bash
# shell_unlimited.sh — NEVER let truncation happen
# Source this: source /mnt/agents/output/.bg_logs/shell_unlimited.sh
# Then use: u "your command" to get full untruncated output

U_DIR="/mnt/agents/output/.bg_logs/unlimited"
mkdir -p "$U_DIR"

u() {
    local cmd="$1"
    local id="u_$(date +%s)_$RANDOM"
    local out="$U_DIR/${id}.txt"
    local meta="$U_DIR/${id}.meta"
    
    echo "[U] Running: $cmd" >&2
    
    # Run with full capture, no truncation
    { time eval "$cmd" ; } > "$out" 2>&1
    local rc=$?
    local size=$(wc -c < "$out")
    local parts=$(( (size + 8499) / 8500 ))
    
    # Write metadata
    cat > "$meta" << EOF
{"id":"$id","cmd":"$cmd","rc":$rc,"size":$size,"parts":$parts,"file":"$out"}
EOF
    
    echo "[U] DONE | ID: $id | Size: ${size}b | Parts: $parts | RC: $rc" >&2
    
    # If small enough, show inline
    if [ "$size" -le 8500 ]; then
        cat "$out"
    else
        echo "[U] OUTPUT TOO LARGE — use: uread $id [part]" >&2
        echo "[U] Or: ucat $id" >&2
    fi
    echo "$id"
}

uread() {
    local id="$1"
    local part="${2:-0}"
    local out="$U_DIR/${id}.txt"
    [ ! -f "$out" ] && echo "[U] Not found: $id" >&2 && return 1
    local size=$(wc -c < "$out")
    local offset=$((part * 8500))
    [ "$offset" -ge "$size" ] && echo "[U] Part $part beyond $size" >&2 && return 1
    echo "=== $id | part $part | offset $offset | total $size ==="
    tail -c +$((offset + 1)) "$out" | head -c 8500
}

ucat() {
    local id="$1"
    local out="$U_DIR/${id}.txt"
    local meta="$U_DIR/${id}.meta"
    [ ! -f "$out" ] && echo "[U] Not found: $id" >&2 && return 1
    local size=$(wc -c < "$out")
    local parts=$(( (size + 8499) / 8500 ))
    for p in $(seq 0 $((parts - 1))); do
        echo ""
        uread "$id" "$p"
    done
}

uls() {
    ls -lt "$U_DIR"/*.meta 2>/dev/null | head -20
}

uinfo() {
    local id="$1"
    cat "$U_DIR/${id}.meta" 2>/dev/null || echo "[U] Not found"
}
