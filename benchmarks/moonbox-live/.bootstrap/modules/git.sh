#!/bin/bash
# git.sh — Git operations using persistent gitw

GITW="/mnt/agents/output/gitw"
REPO_ROOT="/mnt/agents/output"

gitw() {
    "$GITW" "$@"
}

git_status_all() {
    for dir in "$REPO_ROOT"/*/; do
        [ -d "$dir/.git" ] || [ -d "/mnt/agents/output/.git_repos/$(basename $dir).git" ] || continue
        cd "$dir"
        local status=$("$GITW" status --short 2>/dev/null)
        [ -n "$status" ] && echo "=== $(basename $dir) ===" && echo "$status"
    done
}

git_push_all() {
    export GITHUB_PAT="${GITHUB_PAT:-}"
    for dir in "$REPO_ROOT"/*/; do
        [ -d "/mnt/agents/output/.git_repos/$(basename $dir).git" ] || continue
        cd "$dir"
        local branch=$("$GITW" branch --show-current 2>/dev/null || echo "master")
        "$GITW" remote set-url origin "https://${GITHUB_PAT}@github.com/toxicwind/$(basename $dir).git" 2>/dev/null || true
        "$GITW" push origin "$branch" 2>/dev/null && echo "[OK] $(basename $dir)" || echo "[FAIL] $(basename $dir)"
    done
}

sync_wrappers() {
    for dir in "$REPO_ROOT"/*/; do
        [ -d "$dir" ] || continue
        [ -f "$dir/.gitignore" ] || continue
        cp -r /mnt/agents/output/.wrappers "$dir/" 2>/dev/null || true
        cd "$dir"
        "$GITW" add .wrappers/ 2>/dev/null || true
        "$GITW" commit -m "sync: wrappers from master" 2>/dev/null || true
    done
}
