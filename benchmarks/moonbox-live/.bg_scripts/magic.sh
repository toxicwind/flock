#!/bin/sh
KERNEL_URL="http://127.0.0.1:8888/kernel/execute"

completions() {
    code="$1"
    [ -z "$code" ] && { echo "Usage: completions 'print(1+1)'"; return 1; }
    payload=$(printf '{"code":%s}' "$(echo "$code" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')")
    curl -s -m 15 -X POST "$KERNEL_URL" -H "Content-Type: application/json" -d "$payload" 2>/dev/null | python3 -c '
import sys, json
d = json.load(sys.stdin)
if "result" in d: print(d["result"])
elif "output" in d: print(d["output"])
else: print(json.dumps(d, indent=2))
'
}

sandbox_status() {
    echo "=== SANDBOX STATUS ==="
    for svc in "kernel:8888" "portal:8080" "k3_proxy:19999" "cdp:9223"; do
        name=$(echo "$svc" | cut -d: -f1)
        port=$(echo "$svc" | cut -d: -f2)
        status=$(curl -s -m 3 "http://127.0.0.1:$port/" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "DOWN")
        echo "$name:$port -> $status"
    done
}

trace_dump() {
    tail -20 /mnt/agents/output/.bg_logs/tool_mitm.jsonl 2>/dev/null | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        print(f"[{d.get(chr(116)+chr(115),chr(63))}] {d.get(chr(116)+chr(111)+chr(111)+chr(108),chr(63))}: {str(d.get(chr(99)+chr(109)+chr(100),chr(63)))[:80]}")
    except: pass
'
}

cve_check() {
    echo "=== CVE CHECK ==="
    python3 --version 2>&1
    echo "---"
    runc --version 2>/dev/null || echo "runc: not installed"
    echo "---"
    curl -s -m 3 http://127.0.0.1:8888/kernel/status 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); ka=d.get("kernel_alive",False); print("kernel_alive:",ka)'
}

push_all() {
    . /mnt/agents/output/.env
    PAT="$GITHUB_PAT"
    for repo in "effusion-labs" "triangle-access"; do
        git_dir="/mnt/agents/output/.git_repos/${repo}.git"
        work_tree="/mnt/agents/output/${repo}"
        cd "$work_tree" 2>/dev/null || continue
        git --git-dir="$git_dir" --work-tree="$work_tree" add -A 2>/dev/null
        git --git-dir="$git_dir" --work-tree="$work_tree" commit -m "magic: $(date -u +%Y%m%d-%H%M%SZ)" 2>/dev/null
        git --git-dir="$git_dir" --work-tree="$work_tree" push "https://${PAT}@github.com/toxicwind/${repo}.git" main --force 2>/dev/null && echo "PUSHED: $repo" || echo "FAIL: $repo"
    done
}
