#!/bin/bash
# git-wrapper.sh v6.1 — FUSE-BAN, tmpfs-only
gitw() {
    local repo_name=$(basename $(pwd))
    local git_dir=/tmp/.git_repos/${repo_name}.git
    local work_tree=/tmp/${repo_name}
    rm -f $git_dir/*.lock 2>/dev/null || true
    if [ ! -d $git_dir ]; then
        mkdir -p $git_dir
        git init --bare $git_dir 2>/dev/null
    fi
    git --git-dir=$git_dir --work-tree=$work_tree "$@"
}
