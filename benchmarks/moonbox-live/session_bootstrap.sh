#!/bin/sh
# Arc-AGI Session Bootstrap - Run at start of every session
. /mnt/agents/output/chatty_env.sh

# Verify secrets
if [ -z "$JWT_SECRET" ]; then
    echo "§JWT_MISSING§"
    exit 1
fi

# Reset session
python3 /mnt/agents/output/autohook_final.py 2>/dev/null || true

# Verify packages
python3 -c "import aiohttp; import jwt; print('§PACKAGES_OK§')" 2>/dev/null || echo "§PACKAGES_MISSING§"

echo "§BOOTSTRAP_COMPLETE§"
