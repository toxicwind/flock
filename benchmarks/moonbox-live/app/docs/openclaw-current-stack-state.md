# OpenClaw Current Stack State (Living)

Last updated: 2026-03-12

This file is the authoritative, continuously updated snapshot of the live OpenClaw + GHAS stack in this workspace.

## Runtime snapshot

- OpenClaw runtime: `2026.3.3`
- OpenClaw config path: `~/.openclaw/openclaw.json`
- Gateway:
  - bind: `127.0.0.1` (loopback)
  - port: `18789`
  - mode: local + Tailscale serve
  - Control UI: enabled

## Channel state

- Telegram: enabled, configured, running (polling)
- Discord: enabled, configured, running; currently reports `disconnected` while probe still reports channel as workable

## MCP wiring (fixed on 2026-03-12)

`~/.codex/config.toml` MCP command paths were corrected to point at the real operator scripts:

- `/home/toxic/apex-workspace/projects/github/toxicwind/labs-apex-operator/scripts/mcp/playwright_fork_runner.sh`
- `/home/toxic/apex-workspace/projects/github/toxicwind/labs-apex-operator/scripts/mcp/openclaw_local_runner.sh`
- `/home/toxic/apex-workspace/projects/github/toxicwind/labs-apex-operator/scripts/mcp/tmux_local_runner.sh`
- `/home/toxic/apex-workspace/projects/github/toxicwind/labs-apex-operator/scripts/mcp/ghas_local_runner.sh`

## GHAS (GitHub Advanced Search MCP) state

- GHAS repo root (fixed):
  - `/home/toxic/apex-workspace/projects/github/toxicwind/github-advanced-search-mcp`
- `apex ghas` default `GHAS_ROOT` was aligned to this path in:
  - `labs-apex-operator/scripts/mcp/ghas_local_runner.sh`
  - `labs-apex-operator/bin/apex`
- Dependency bootstrap completed with `bun install`
- GHAS services currently healthy:
  - API: `127.0.0.1:35161`
  - MCP: `127.0.0.1:35162`
  - Frontend: `http://127.0.0.1:35160`

## OpenClaw-specific repo integration

Integrated in local clone workspace:

- `/home/toxic/apex-workspace/apex-clone/github/openclaw/community`
- `/home/toxic/apex-workspace/apex-clone/github/openclaw/openclaw`
- `/home/toxic/apex-workspace/apex-clone/github/openclaw/skills`

Primary Discord-specific OpenClaw repository:

- `openclaw/community` (Discord server policies/docs)

## Known warnings / follow-up

- Gateway warning: config token differs from service token.
  - Recommended sync action: reinstall/update gateway service token so service and config match.
- Additional gateway-like units are still detected on host; single-gateway enforcement should remain a hygiene goal unless intentionally multi-gateway.

## Update protocol

When stack behavior changes, update this document in the same change set as config/runtime edits:

1. Run validation probes (OpenClaw + GHAS)
2. Update runtime/channel/MCP sections
3. Record warnings/regressions explicitly
4. Keep secrets redacted (never paste tokens/passwords)
