#!/usr/bin/env bash
# Auto-loader for agents/dot ecosystem
export PATH="/mnt/agents/dot/bin:/usr/local/bin:$PATH"
: ${GH_PAT:?"GH_PAT must be exported"}
export PYTHONPATH="/mnt/agents/dot/lib:$PYTHONPATH"
alias ag="python3 /mnt/agents/dot/bin/auto-git.py"
alias s="/mnt/agents/dot/bin/strace-hotfix"
alias n="/mnt/agents/dot/bin/net-detect"
alias rb="/usr/local/bin/%%rootbash"
