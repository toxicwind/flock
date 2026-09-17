#!/bin/bash
export GIT_DIR=/mnt/agents/dot/_git
export GIT_WORK_TREE=/mnt/agents/dot
cd /mnt/agents/dot
git add -A 2>/dev/null
git commit -m "auto: $(date -Iseconds)" 2>/dev/null || true
git push origin main --force 2>/dev/null || true
