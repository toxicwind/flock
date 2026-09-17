#!/usr/bin/env bash
set -euo pipefail
cd /mnt/agents/dot
if git diff --quiet HEAD 2>/dev/null; then
  echo "No changes to commit"
  exit 0
fi
git add -A
git commit -m "auto: $(date -Iseconds)" 2>/dev/null || true
git push origin main 2>/dev/null || true
