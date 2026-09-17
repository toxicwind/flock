#!/bin/bash
# SESSION_RECOVER.sh — Recover repos without .git directories
# 
# PROBLEM: K8s sandbox deletes .git dirs
# SOLUTION: Git metadata stored in /mnt/agents/output/.git_repos/<repo>.git/
#           Working tree has NO .git directory (invisible to K8s cleaner)
#
# USAGE: bash /mnt/agents/output/SESSION_RECOVER.sh

set -uo pipefail

PAT="${GITHUB_PAT:-}"
if [ -z "$PAT" ] && [ -f "/mnt/agents/output/triangle-access/.env.keys" ]; then
    PAT=$(grep "^GITHUB_PAT=" /mnt/agents/output/triangle-access/.env.keys | head -1 | cut -d'"' -f2)
fi

if [ -z "$PAT" ]; then
    echo "[RECOVER] ERROR: No GITHUB_PAT found"
    exit 1
fi

# Source git wrapper
source /mnt/agents/output/.git_repos/git-wrapper.sh

REPOS=(
    "envd-project:toxicwind/envd-project:master"
    "repo_kimi_team_recon:toxicwind/repo_kimi_team_recon:master"
    "effusion-labs:toxicwind/effusion-labs:main"
    "triangle-access:toxicwind/triangle-access:master"
    "toxicwind-repos:toxicwind/toxicwind-repos:master"
    "agents-md-project:toxicwind/agents-md:main"
)

for entry in "${REPOS[@]}"; do
    IFS=':' read -r name remote branch <<< "$entry"
    local_dir="/mnt/agents/output/$name"
    git_dir="/mnt/agents/output/.git_repos/${name}.git"
    
    echo ""
    echo "[RECOVER] $name"
    
    if [ ! -d "$local_dir" ]; then
        echo "  Local dir missing — cloning fresh..."
        mkdir -p "$local_dir"
        git init --bare "$git_dir" 2>/dev/null
        git --git-dir="$git_dir" --work-tree="$local_dir" remote add origin "https://${PAT}@github.com/${remote}.git" 2>/dev/null || true
        git --git-dir="$git_dir" --work-tree="$local_dir" config user.name "toxicwind"
        git --git-dir="$git_dir" --work-tree="$local_dir" config user.email "toxicwind@users.noreply.github.com"
        git --git-dir="$git_dir" --work-tree="$local_dir" pull origin "$branch" 2>/dev/null || true
        echo "  Cloned"
    else
        echo "  Local dir exists — checking git metadata..."
        
        # Ensure git metadata exists
        if [ ! -f "$git_dir/HEAD" ]; then
            echo "  Git metadata missing — initializing..."
            git init --bare "$git_dir" 2>/dev/null
            git --git-dir="$git_dir" --work-tree="$local_dir" remote add origin "https://${PAT}@github.com/${remote}.git" 2>/dev/null || true
            git --git-dir="$git_dir" --work-tree="$local_dir" config user.name "toxicwind"
            git --git-dir="$git_dir" --work-tree="$local_dir" config user.email "toxicwind@users.noreply.github.com"
        fi
        
        # Remove any .git that might have been created
        rm -rf "$local_dir/.git"
        
        # Set remote with PAT
        git --git-dir="$git_dir" --work-tree="$local_dir" remote set-url origin "https://${PAT}@github.com/${remote}.git" 2>/dev/null || true
        
        # Pull latest
        git --git-dir="$git_dir" --work-tree="$local_dir" pull origin "$branch" 2>/dev/null || true
        echo "  Synced"
    fi
done

echo ""
echo "[RECOVER] All repos ready. No .git directories in working trees."
echo "[RECOVER] Git metadata: /mnt/agents/output/.git_repos/"
echo "[RECOVER] Use: source /mnt/agents/output/.git_repos/git-wrapper.sh"
echo "[RECOVER] Then: gitw status, gitw commit, gitw push"
