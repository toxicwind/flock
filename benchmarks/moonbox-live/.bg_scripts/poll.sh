#!/bin/bash
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export GITHUB_PAT="${GITHUB_PAT}"
while true; do
  curl -s -H "Authorization: token ${GITHUB_PAT}"     "https://api.github.com/repos/toxicwind/effusion-labs/actions/runs?per_page=1" |     python3 -c "import sys,json,datetime; d=json.load(sys.stdin); r=d.get('workflow_runs',[{}])[0]; print(f\"[{datetime.datetime.now().isoformat()}] {r.get('status','?')} | {r.get('conclusion','?')} | {r.get('head_sha','?')[:8]}\")"     >> /mnt/agents/output/.bg_logs/actions-poll.log 2>&1
  sleep 15
done
