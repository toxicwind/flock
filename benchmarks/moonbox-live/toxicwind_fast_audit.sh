#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# TOXICWIND FAST AUDIT — 100 repos, shallow clone, max parallel, 5s timeout
# ═══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

USER="toxicwind"
GITHUB_PAT=$(grep "^GITHUB_PAT=" /mnt/agents/output/triangle-access/.env.keys | head -1 | cut -d'"' -f2)
export GITHUB_PAT

AUDIT_DIR="/tmp/tw_audit_$$"
mkdir -p "$AUDIT_DIR/repos"
REPORT="/mnt/agents/output/reports/toxicwind_audit_$(date +%Y%m%d_%H%M%S).json"
mkdir -p "$(dirname "$REPORT")"

# Fetch all repo URLs
REPOS=$(curl -s -H "Authorization: Bearer $GITHUB_PAT" "https://api.github.com/users/$USER/repos?type=all&per_page=100" | grep '"clone_url"' | sed 's/.*"clone_url": "\([^"]*\)".*/\1/')
TOTAL=$(echo "$REPOS" | wc -l)

echo "🔍 Fast audit: $TOTAL repos | Workers: 32 | Depth: 1 | Timeout: 5s"
echo ""

# Worker
scan_one() {
    local url="$1" idx="$2"
    local name=$(basename "$url" .git)
    local dir="$AUDIT_DIR/repos/$name"
    local out="$AUDIT_DIR/${idx}_${name}.json"
    
    # Shallowest clone possible
    timeout 5 git clone --depth 1 --single-branch "$url" "$dir" 2>/dev/null || { echo "CLONE_FAIL:$name"; return; }
    
    # Fast gitleaks (no-git mode, 5MB max, 5s timeout)
    local findings=$(timeout 5 gitleaks detect --source "$dir" --no-git --max-target-megabytes 5 -r /tmp/gl_$$_${idx}.json 2>/dev/null; cat /tmp/gl_$$_${idx}.json 2>/dev/null | grep -v '^\[\]$' || true)
    rm -f /tmp/gl_$$_${idx}.json
    
    # Immediate cleanup
    rm -rf "$dir"
    
    if [ -n "$findings" ] && [ "$findings" != "[]" ]; then
        echo "{"\"repo\"":\""$name"\"","\"status\"":\""DIRTY"\"","\"findings\"":$(echo "$findings" | head -5 | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().splitlines()))' 2>/dev/null || echo "[]")}" > "$out"
        echo "DIRTY:$name"
    else
        echo "{"\"repo\"":\""$name"\"","\"status\"":\""CLEAN"\""}" > "$out"
        echo "CLEAN:$name"
    fi
}

export -f scan_one
export AUDIT_DIR

# Launch all in parallel with xargs (max 32)
echo "$REPOS" | xargs -P 32 -I {} bash -c 'scan_one "$@"' _ {} $(seq 1 $TOTAL) 2>/dev/null | while read line; do
    if [[ "$line" == DIRTY:* ]]; then
        printf "\r   ⚠️  %-50s SECRETS!\n" "${line#DIRTY:}"
    elif [[ "$line" == CLEAN:* ]]; then
        printf "\r   ✅ %-50s clean" "${line#CLEAN:}"
    fi
done

echo ""
echo ""

# Aggregate
echo "[" > "$REPORT"
FIRST=1
CLEAN=0
DIRTY=0
for f in "$AUDIT_DIR"/*.json; do
    [ -e "$f" ] || continue
    if [ "$FIRST" -eq 1 ]; then FIRST=0; else echo "," >> "$REPORT"; fi
    cat "$f" >> "$REPORT"
    if grep -q '"status":"CLEAN"' "$f" 2>/dev/null; then CLEAN=$((CLEAN+1)); else DIRTY=$((DIRTY+1)); fi
done
echo "" >> "$REPORT"
echo "]" >> "$REPORT"

rm -rf "$AUDIT_DIR"

echo "✅ Done | Clean: $CLEAN | Dirty: $DIRTY | Report: $REPORT"
[ "$DIRTY" -gt 0 ] && exit 1 || exit 0
