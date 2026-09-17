#!/bin/bash
cd /mnt/agents/output/triangle-access/src/frontend
export PATH="/usr/bin:/usr/local/bin:$PATH"
echo "[$(date -Iseconds)] BUILD STARTED" > /mnt/agents/output/.bg-build/status.log
node node_modules/next/dist/bin/next build >> /mnt/agents/output/.bg-build/build.log 2>&1
EXIT=$?
echo "[$(date -Iseconds)] BUILD EXIT CODE: $EXIT" >> /mnt/agents/output/.bg-build/status.log
