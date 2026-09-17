#!/bin/sh
# First-class chatty secret - source this everywhere
export JWT_SECRET="chatty"
export KIMI_JWT_SECRET="chatty"  
export CHATTY_SECRET="chatty"
: ${GITHUB_PAT:?"GITHUB_PAT must be exported"}
export PYTHONPATH="/mnt/agents/output/.pip:$PYTHONPATH"
