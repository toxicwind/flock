#!/bin/sh
set -e

. /mnt/agents/output/.env
PAT="$GITHUB_PAT"

# --- effusion-labs ---
cd /mnt/agents/output/app
git --git-dir=/mnt/agents/output/.git_repos/effusion-labs.git --work-tree=/mnt/agents/output/app add -A
git --git-dir=/mnt/agents/output/.git_repos/effusion-labs.git --work-tree=/mnt/agents/output/app commit --allow-empty -m "prod: bootstrap, dash hooks, fsync none $(date -u +%Y%m%d-%H%M%SZ)" || true
git --git-dir=/mnt/agents/output/.git_repos/effusion-labs.git --work-tree=/mnt/agents/output/app push "https://${PAT}@github.com/toxicwind/effusion-labs.git" main --force
echo "---EF PUSHED---"

# --- triangle-access ---
cd /mnt/agents/output/triangle-access
git --git-dir=/mnt/agents/output/.triangle-git-metadata --work-tree=/mnt/agents/output/triangle-access add -A
git --git-dir=/mnt/agents/output/.triangle-git-metadata --work-tree=/mnt/agents/output/triangle-access commit --allow-empty -m "prod: sync $(date -u +%Y%m%d-%H%M%SZ)" || true
git --git-dir=/mnt/agents/output/.triangle-git-metadata --work-tree=/mnt/agents/output/triangle-access push "https://${PAT}@github.com/toxicwind/triangle-access.git" main --force
echo "---TA PUSHED---"

# --- verify CI ---
sleep 3
curl -s -H "Authorization: token ${PAT}" \
  "https://api.github.com/repos/toxicwind/effusion-labs/actions/runs?per_page=3" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'CI:{r[\"status\"]}|{r[\"conclusion\"]}|{r[\"head_sha\"][:8]}') for r in d.get('workflow_runs', [])[:3]]"
