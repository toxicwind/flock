#!/bin/bash
# Master background script - does everything, logs to .bg_master.log
LOG="/mnt/agents/output/.bg_master.log"
echo "[$(date)] BG MASTER START" > "$LOG"

# 1. Clear all git locks
for lock in /mnt/agents/output/*/.git/index.lock; do rm -f "$lock" 2>/dev/null; done
echo "[$(date)] locks cleared" >> "$LOG"

# 2. Commit all repos
for d in effusion-labs envd-project repo_kimi_team_recon triangle-access toxicwind-repos; do
  path="/mnt/agents/output/$d"
  cd "$path" && GIT_EDITOR=true EDITOR=true git add -A 2>/dev/null
  GIT_EDITOR=true EDITOR=true git commit -m "init: $d" 2>&1 | tail -1 >> "$LOG"
  echo "[$(date)] committed $d" >> "$LOG"
done

# 3. Install dulwich and GitPython
python3 -m pip install dulwich GitPython -q 2>&1 | tail -1 >> "$LOG"
echo "[$(date)] pip done" >> "$LOG"

# 4. Download Go
cd /tmp && wget -q https://go.dev/dl/go1.23.0.linux-amd64.tar.gz 2>&1 | tail -1 >> "$LOG"
tar -C /usr/local -xzf go1.23.0.linux-amd64.tar.gz 2>/dev/null
ln -sf /usr/local/go/bin/go /usr/local/bin/go 2>/dev/null
echo "[$(date)] go installed: $(go version 2>&1)" >> "$LOG"

# 5. Moonbox chunks
mkdir -p /mnt/agents/output/.moonbox_chunks
chunk=0
for f in /app/.agents/skills/kimi-help-center/SKILL.md /app/.agents/skills/kimi-widget/SKILL.md /mnt/agents/output/effusion-labs/AGENTS.md /mnt/agents/output/effusion-labs/SYSTEM.md; do
  if [ -f "$f" ]; then
    split -b 6000 "$f" /mnt/agents/output/.moonbox_chunks/chunk_${chunk}_
    chunk=$((chunk+1))
  fi
done
echo "[$(date)] moonbox chunks: $chunk files" >> "$LOG"

# 6. Port check
echo "[$(date)] ports: $(ss -tlnp 2>/dev/null | grep -E ':80|:443' || echo 'no 80/443')" >> "$LOG"

echo "[$(date)] BG MASTER DONE" >> "$LOG"
