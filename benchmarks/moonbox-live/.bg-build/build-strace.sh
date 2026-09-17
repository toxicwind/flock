#!/bin/bash
cd /mnt/agents/output/triangle-access/src/frontend
export PATH="/usr/bin:/usr/local/bin:$PATH"
echo "[$(date -Iseconds)] STRACE BUILD STARTED" > /mnt/agents/output/.bg-build/status.log
strace -f -e trace=openat,read,write,execve,access -o /mnt/agents/output/.bg-build/strace.log node node_modules/next/dist/bin/next build 2>&1 | tee /mnt/agents/output/.bg-build/build.log
EXIT=$?
echo "[$(date -Iseconds)] BUILD EXIT CODE: $EXIT" >> /mnt/agents/output/.bg-build/status.log
