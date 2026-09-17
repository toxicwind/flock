#!/bin/bash
export PATH="/root/.bun/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export HOME="/root"
export CI="true"
export PUPPETEER_SKIP_DOWNLOAD="1"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD="1"
export GITHUB_PAT="${GITHUB_PAT}"

cd /mnt/agents/output/app

echo "[$(date -Iseconds)] BUILD START" > /mnt/agents/output/.bg_logs/build.log
/root/.bun/bin/bun install 2>&1 | tail -10 >> /mnt/agents/output/.bg_logs/build.log
/root/.bun/bin/bun run build 2>&1 | tail -20 >> /mnt/agents/output/.bg_logs/build.log
BUILD_RC=$?
echo "[$(date -Iseconds)] BUILD DONE rc=$BUILD_RC" >> /mnt/agents/output/.bg_logs/build.log

if [ $BUILD_RC -eq 0 ]; then
  git config user.email "agent@many-never-one.local"
  git config user.name "ManyNeverOne Agent"
  git add -A
  git commit -m "auto: build success $(date -u +%Y%m%d-%H%M%SZ)" 2>/dev/null || true
  git push "https://${GITHUB_PAT}@github.com/toxicwind/effusion-labs.git" main 2>&1 | tail -5 >> /mnt/agents/output/.bg_logs/build.log
fi
echo "done" > /mnt/agents/output/.build_done
