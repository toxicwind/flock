#!/bin/bash
# FLUIDPRISM OP: MILDLYAWESOME_AUDIT_V5 (Effusion Labs Edition)
# Purpose: Deep recovery scan for effusion_labs_final repo
# Usage: chmod +x mildlyawesome_audit_effusion.sh && ./mildlyawesome_audit_effusion.sh

REPO_ROOT="/home/toxic/development/effusion_labs_final"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GREY='\033[0;90m'
NC='\033[0m'

echo -e "${BLUE}>>> 🛑 MILDLYAWESOME AUDIT: EFFUSION LABS FINAL${NC}"
echo ">>> TARGET: $REPO_ROOT"

if [ ! -d "$REPO_ROOT" ]; then
    echo -e "${RED}❌ CRITICAL: Repo root not found.${NC}"
    exit 1
fi
cd "$REPO_ROOT" || exit 1

# STATE DIAGNOSIS
echo ""
echo -e "${BLUE}--- [PHASE 0] REPOSITORY STATE DIAGNOSIS ---${NC}"

if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    echo -e "${RED}🚨 REPOSITORY IN REBASE STATE${NC}"
    if [ -f ".git/rebase-merge/head-name" ]; then
        BRANCH=$(cat .git/rebase-merge/head-name)
        echo -e "    Rebasing Branch: ${CYAN}$BRANCH${NC}"
    fi
    echo -e "    ${YELLOW}Action: 'git rebase --abort' to recover${NC}"
else
    echo -e "${GREEN}✅ Repository state: NOMINAL${NC}"
fi

# SEARCH VECTORS FOR EFFUSION LABS
VECTORS=(
    "PORTAINER_WEBHOOK|Deployment webhook"
    "GITHUB_TOKEN|Release upload token"
    "artifact_sync.sh|Artifact sync script"
    "generate-artifacts.sh|Artifact generation"
    "cannabis|Cannabis API integration"
    "WeedmapsScraper|Weedmaps integration"
)

echo ""
echo -e "${BLUE}--- [PHASE 2] GOD-EYE GREP ---${NC}"

for vector in "${VECTORS[@]}"; do
    IFS='|' read -r TERM DESC <<< "$vector"
    echo ""
    echo -e "🔎 ${MAGENTA}'$TERM'${NC} ($DESC)"
    
    HITS=$(git grep -I -n "$TERM" $(git rev-list --all --max-count=2000 2>/dev/null) 2>/dev/null | head -n 5)
    
    if [ -n "$HITS" ]; then
        echo "$HITS" | while read -r line; do
            COMMIT=$(echo "$line" | cut -d':' -f1)
            FILE=$(echo "$line" | cut -d':' -f2)
            
            echo -e "    ${GREEN}[FOUND]${NC} ${CYAN}${COMMIT:0:7}${NC} | ${YELLOW}$FILE${NC}"
            echo -e "      └-> git show $COMMIT:\"$FILE\""
        done
    else
        echo -e "    ${GREY}No hits in commit history${NC}"
    fi
done

echo ""
echo -e "${BLUE}>>> AUDIT COMPLETE${NC}"
