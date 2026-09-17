#!/bin/sh
# Session init - run at start of every new session
: ${GITHUB_PAT:?"GITHUB_PAT must be exported"}
export PYTHONPATH="/mnt/agents/output/.pip:$PYTHONPATH"
chmod -R 777 /mnt/agents/output/.pip 2>/dev/null
# Verify key packages
python3 -c "import aiohttp; import psutil; print('§PACKAGES_OK§')" 2>/dev/null || echo "§PACKAGES_MISSING§"
