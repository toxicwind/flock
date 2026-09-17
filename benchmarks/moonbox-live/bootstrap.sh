#!/bin/sh
# Production bootstrap for ANY Kimi container
# Run this on every fresh session

export HOME=/root
export PATH="/root/.cargo/bin:/root/.bun/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# 1. Source secrets
[ -f /mnt/agents/output/.env ] && . /mnt/agents/output/.env

# 2. Git aliases (dash-compatible)
git_ef() { git --git-dir=/mnt/agents/output/.git_repos/effusion-labs.git --work-tree=/mnt/agents/output/app "$@"; }
git_ta() { git --git-dir=/mnt/agents/output/.triangle-git-metadata --work-tree=/mnt/agents/output/triangle-access "$@"; }

# 3. Fast git config
git config --global core.preloadIndex true
git config --global core.fsync none
git config --global core.untrackedCache false
git config --global core.checkStat minimal
git config --global advice.detachedHead false
git config --global --add safe.directory /mnt/agents/output/.git_repos/effusion-labs.git
git config --global --add safe.directory /mnt/agents/output/.triangle-git-metadata

# 4. Fake tmp
export TMPDIR=/mnt/agents/output/fake_tmp
export TEMP=/mnt/agents/output/fake_tmp
mkdir -p /mnt/agents/output/fake_tmp

# 5. Verify tools
[ -x /root/.bun/bin/bun ] || curl -fsSL https://bun.sh/install | bash
[ -x /usr/local/bin/rg ] || (curl -sL https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz | tar xz && mv ripgrep-*/rg /usr/local/bin/rg)
[ -x /usr/local/bin/fd ] || (curl -sL https://github.com/sharkdp/fd/releases/download/v10.1.0/fd-v10.1.0-x86_64-unknown-linux-musl.tar.gz | tar xz && mv fd-*/fd /usr/local/bin/fd)

echo "BOOTSTRAP COMPLETE"
