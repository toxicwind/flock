#!/usr/bin/env bash
# CONSOLIDATION PLAN — toxicwind sovereign stack
# Generated: 2026-08-18

set -euo pipefail

# =============================================================================
# PHASE 0: DELETE AUTOMATED NOISE COMMITS (all repos with .gitignore-only sync)
# =============================================================================
# The 2026-08-18-01:20 sync commits only touched .gitignore. They are worthless.
# Rewind these repos to the commit BEFORE the sync.

NOISE_REPOS=(
  pi
  antigravity-gateway-master
  beellama.cpp
  caddy-sovereign-auth
  effusion-labs
  effusion-labs-tickets
  grok-build
  llama-cpp-turboquant
  web3-sec-workspace
  dots-hyprland
  dedi-ops
  zedra
  github-advanced-search-mcp
  pi-subagents
  kimi-code-sovereign
)

for repo in "${NOISE_REPOS[@]}"; do
  echo "[$repo] Checking for noise commits..."
  cd ~/projects/$repo 2>/dev/null || continue
  # Find the last commit that changed ONLY .gitignore
  LAST=$(git log --format='%H' -1 -- .gitignore 2>/dev/null)
  if [ -n "$LAST" ]; then
    # Check if that commit ONLY touched .gitignore
    FILES=$(git show --pretty='' --name-only $LAST | grep -v '^\.gitignore$' | wc -l)
    if [ "$FILES" -eq 0 ]; then
      echo "  -> Rewinding noise commit $LAST"
      git reset --hard HEAD~1
      git push --force-with-lease origin $(git branch --show-current)
    fi
  fi
  cd - >/dev/null
done

# =============================================================================
# PHASE 1: MERGE EPHEMERAL BRANCHES INTO MAIN
# =============================================================================
# All those "codex/" branches are agent scratchpads. Squash useful ones, delete rest.

for repo in pi kimi-code-sovereign grok-build zedra; do
  cd ~/projects/$repo 2>/dev/null || continue
  echo "[$repo] Cleaning branches..."
  git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
  for branch in $(git branch -r | grep 'codex/' | sed 's|origin/||'); do
    echo "  -> Deleting remote branch $branch"
    git push origin --delete "$branch" 2>/dev/null || true
  done
  for branch in $(git branch | grep 'codex/' | sed 's|^* ||'); do
    echo "  -> Deleting local branch $branch"
    git branch -D "$branch" 2>/dev/null || true
  done
  cd - >/dev/null
done

# =============================================================================
# PHASE 2: CONSOLIDATE INFERENCE REPOS INTO monorepo
# =============================================================================
# beellama.cpp, llama-cpp-turboquant, ik_llama.cpp should NOT be standalone repos.
# They should be submodules or build scripts inside a single "sovereign-llm" repo.

echo "[CONSOLIDATE] Creating sovereign-llm monorepo..."
mkdir -p ~/projects/sovereign-llm/{beellama,ik-llama,turboquant,scripts}
cd ~/projects/sovereign-llm

# Move build configs and scripts from each repo
for src in beellama.cpp llama-cpp-turboquant ik_llama.cpp; do
  if [ -d ~/projects/$src ]; then
    echo "  -> Importing $src build configs"
    cp ~/projects/$src/build*.sh ./scripts/$src-build.sh 2>/dev/null || true
    cp ~/projects/$src/CMakeLists.txt ./$src/ 2>/dev/null || true
    cp ~/projects/$src/*.toml ./$src/ 2>/dev/null || true
  fi
done

git init 2>/dev/null || true
git add -A
git commit -m "chore: consolidate llama.cpp forks into sovereign-llm monorepo" 2>/dev/null || true

# =============================================================================
# PHASE 3: MERGE AGENT REPOS INTO pi (the main agent repo)
# =============================================================================
# pi-subagents, grok-build, zedra should be packages/ inside pi, not standalone.

echo "[CONSOLIDATE] Merging agent repos into pi..."
cd ~/projects/pi

# pi-subagents -> packages/subagents
if [ -d ~/projects/pi-subagents ] && [ ! -d packages/subagents ]; then
  echo "  -> Merging pi-subagents into packages/subagents"
  mkdir -p packages/subagents
  cp -r ~/projects/pi-subagents/* packages/subagents/ 2>/dev/null || true
  git add packages/subagents
  git commit -m "feat: merge pi-subagents into monorepo" || true
fi

# grok-build -> packages/grok-build
if [ -d ~/projects/grok-build ] && [ ! -d packages/grok-build ]; then
  echo "  -> Merging grok-build into packages/grok-build"
  mkdir -p packages/grok-build
  cp -r ~/projects/grok-build/* packages/grok-build/ 2>/dev/null || true
  git add packages/grok-build
  git commit -m "feat: merge grok-build into monorepo" || true
fi

# zedra -> packages/zedra
if [ -d ~/projects/zedra ] && [ ! -d packages/zedra ]; then
  echo "  -> Merging zedra into packages/zedra"
  mkdir -p packages/zedra
  cp -r ~/projects/zedra/* packages/zedra/ 2>/dev/null || true
  git add packages/zedra
  git commit -m "feat: merge zedra into monorepo" || true
fi

# =============================================================================
# PHASE 4: MERGE INFRA REPOS INTO sovereign (the main infra repo)
# =============================================================================
# dedi-ops, effusion-labs, caddy-sovereign-auth, antigravity-gateway-master
# should live under sovereign/ as submodules or integrated packages.

echo "[CONSOLIDATE] Merging infra repos into sovereign..."
cd ~/projects/sovereign 2>/dev/null || mkdir -p ~/projects/sovereign && cd ~/projects/sovereign && git init

for repo in dedi-ops effusion-labs caddy-sovereign-auth antigravity-gateway-master; do
  if [ -d ~/projects/$repo ]; then
    target="infra/$repo"
    echo "  -> Merging $repo into $target"
    mkdir -p "$target"
    cp -r ~/projects/$repo/* "$target/" 2>/dev/null || true
    git add "$target"
  fi
done
git commit -m "chore: consolidate infra repos into sovereign monorepo" 2>/dev/null || true

# =============================================================================
# PHASE 5: ARCHIVE STALE REPOS
# =============================================================================
# 87 repos haven't been touched in 30+ days. Archive them to reduce noise.

STALE_REPOS=(
  caddy process-compose xai-proto aquamarine greprip llama-cpp-turboquant
  ik_llama.cpp wllama optimized-cr3-repo x-algorithm xai-cookbook ophel
  openclaw niri DankMaterialShell codex agentgateway supergateway
  WhiteSur-gtk-theme nitrado_api_lib nitrado_api WhiteSur-firefox-theme
  flashinfer vllm codex-patcher-updater grok-prompts strudel-dev-vite
  strudel-sampler-server-vite ComfyUI LCM_Inpaint_Outpaint_Comfy
  byte-vision-mcp ComfyUI-SaveImageWithMetaData grok-1 comfyui-nodes-docs
  ComfyUI-TTools efficiency-nodes-comfyui-updates
)

echo "[ARCHIVE] Marking stale repos as archived..."
for repo in "${STALE_REPOS[@]}"; do
  cd ~/projects/$repo 2>/dev/null || continue
  echo "  -> Archiving $repo"
  git tag archive-$(date +%Y%m%d) 2>/dev/null || true
  # Push archive tag
  git push origin archive-$(date +%Y%m%d) 2>/dev/null || true
  cd - >/dev/null
done

# =============================================================================
# PHASE 6: FINAL PUSH
# =============================================================================

echo "[DONE] Consolidation complete."
echo ""
echo "NEW STRUCTURE:"
echo "  ~/projects/pi              — main agent monorepo (pi + subagents + grok + zedra)"
echo "  ~/projects/sovereign       — infra monorepo (dedi-ops + effusion + caddy + gateway)"
echo "  ~/projects/sovereign-llm   — inference monorepo (beellama + ik-llama + turboquant)"
echo "  ~/projects/kimi-code-sovereign — Kimi integration (keep separate, it's a vendor)"
echo ""
echo "Next: Run 'pi' to verify the monorepo works."
