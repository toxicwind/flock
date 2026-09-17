# PI FORK ARCHITECTURE — System Replacement Plan

## Goal
Replace globally-installed `pi` with local fork at `/home/toxic/projects/pi-agent`.

## Current State (Audited)
- Fork location: `/home/toxic/projects/pi-agent`
- Ahead of origin: 5286 commits
- Untracked files: `packages/tui/src/*.ts` (10 files — need decision)
- Submodules: FIXED (vendor/pi-upstream now at 5cd93f688)
- System `pi`: Unknown location (likely global npm or /usr/local/bin)

## Installation Steps

### 1. Create ~/bin and add to PATH
```bash
mkdir -p ~/bin
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
```

### 2. Install wrappers
```bash
cp /home/toxic/projects/pi-agent/wrapper-pi.sh ~/bin/pi
chmod +x ~/bin/pi
cp /home/toxic/projects/pi-agent/wrapper-grok.sh ~/bin/grok
chmod +x ~/bin/grok
```

### 3. Source bashrc overrides
```bash
cat >> ~/.bashrc << 'EOF'
[bashrc patch content]
EOF
source ~/.bashrc
```

### 4. Verify
```bash
which pi      # Should show ~/bin/pi
pi --version  # Should run fork version
```

## Untracked TUI Files Decision

The 10 untracked files in `packages/tui/src/` are:
- bracketed-paste.ts
- deccara.ts
- desktop-notify.ts
- kitty-graphics.ts
- latex-block.ts
- latex-to-unicode.ts
- loop-watchdog.ts
- mouse.ts
- symbols.ts
- terminal-capabilities.ts
- tmux.ts
- ttyid.ts

**Decision needed:** Are these:
A) New features → `git add` them
B) Generated files → Add to `.gitignore`
C) Experimental → Stash or move to branch

## Model Fix (nemotron context length)

The error:
```
Model: nvidia/nemotron-3-ultra-550b-a55b
Error: 400 Bad Request - Model context length exceeded
Messages: 1166358 tokens > 1000000 limit
```

**Fix:** Change default model in config from nemotron to a model with higher context limit, or implement message truncation/summarization before sending.

Config location to check:
- `/home/toxic/.pi/config.json`
- `/home/toxic/projects/pi-agent/packages/coding-agent/src/config.ts`
- Environment variable: `PI_DEFAULT_MODEL`

## Submodule Strategy

Current submodules (all in `vendor/`):
- `vendor/kimi-code-sovereign` → kimi integration
- `vendor/modelbeats` → model management
- `vendor/oh-my-pi` → shell enhancements
- `vendor/pi-subagents` → subagent system
- `vendor/pi-upstream` → upstream sync (FIXED)
- `vendor/tinker-cookbook` → recipes/templates

All synced and working after the fix.

## Tailscale Services (Already Running)

| Service | URL | Purpose |
|---------|-----|---------|
| File Server | https://awrawr-pc-1.tailc9ac71.ts.net/files/ | Static file hosting |
| Command Server | https://awrawr-pc-1.tailc9ac71.ts.net/cmd | Remote execution |

Token: `3frZanWTXbqeB0RWdtClB17rzX9mojV4oa29ch6Dkio`

## Maintenance Commands

```bash
# Rebuild fork
npm run build --workspace=packages/coding-agent

# Update submodules
git submodule update --init --recursive --remote

# Check status
git status
npm run check
```
