---
name: backend-building-swarm
description: Swarm-aware backend building that grafts tRPC + Drizzle ORM + Hono onto an existing webapp-building-swarm frontend. Grafts in place on a worktree of the shared repo (created via swarm-workspace) and commits on a backend branch the main agent merges. Supports incremental features (db, auth) and fullstack-template provisioning (--template). Use when the user needs a backend, API, database, server, or authentication in a swarm setup. Requires webapp-building-swarm first.
---

# Backend Building Swarm

**Stack**: tRPC + Drizzle ORM + Hono + MySQL + OAuth 2.0

A swarm-aware backend skill that grafts onto an existing `webapp-building-swarm` project. Adds `api/`, `contracts/`, and optionally `db/` directories — but **never replaces or modifies** existing frontend files.

**Prerequisite**: An existing shared repo created by `webapp-building-swarm` at `/mnt/agents/output/app`.

## Architecture

This skill builds on the **swarm-workspace** two-tier filesystem — a shared
coordination repo (branch hub) plus per-subagent worktrees. See
`swarm-workspace/SKILL.md` for the full contract; it is not restated here.

`init.sh` grafts **in place** on `$PROJECT_PATH` and commits on whatever
branch is checked out there — it does NOT manage worktrees or merge. In the
swarm flow the **main agent** creates the `backend` worktree via
swarm-workspace's `setup-local.sh`, runs `init.sh` in it with `PROJECT_PATH`
pointed at the worktree, commits on the `backend` branch, and merges that
branch into the integration line before page branches fork — so all page
agents inherit the tRPC client and contracts. The main agent runs the graft
itself rather than dispatching a subagent because `init.sh` writes a
**gitignored** `.env` that never travels through the merge: it survives only in
the sandbox where it ran, which must be the main agent's own — the one that
later builds and stages `.env` into the other worktrees. Webapp commit history
is preserved because the `backend` branch descends from the scaffolded frontend.

## Features

Features can be installed incrementally. Base infrastructure (Hono server, tRPC, contracts) is always installed automatically on first run.

| Feature | What it provides | Dependencies |
|---------|-----------------|--------------|
| `db` | Drizzle ORM + MySQL — adds `db/`, `api/queries/connection.ts`, `drizzle.config.ts` | — |
| `auth` | Kimi OAuth + user management — adds `api/kimi/`, Login page, useAuth, AuthLayout | requires `db` (auto-included) |

Default: `init.sh "App"` with no `--features` → defaults to `auth` (= db + auth).

## Scripts

All scripts use absolute paths from `/app/.agents/skills/backend-building-swarm/scripts/`.

### `init.sh` — Backend graft (run inside the `backend` worktree)

```bash
# Point PROJECT_PATH at the backend worktree (created by setup-local.sh first):
PROJECT_PATH=$HOME/app-backend \
  bash /app/.agents/skills/backend-building-swarm/scripts/init.sh "<app-title>" [--features db,auth | --template]
```

- Grafts **in place** on `$PROJECT_PATH` and commits on the currently checked-out branch. In the swarm flow `$PROJECT_PATH` is the main-agent-owned `backend` worktree (the graft is the main agent's own job, not a subagent's — see the gitignored-`.env` reason above); the script's bare default (`/mnt/agents/output/app`) exists only for the deterministic structure test. It does NOT create worktrees or merge.
- Re-entry safe: `.backend-features.json` gates re-runs (adding `--features auth` later only installs the delta). Graft-owned auth UI (`Login.tsx`, `useAuth.ts`, `AuthLayout*`) is planted authoritatively each run, while user-extensible files (`schema.ts`, `seed.ts`, `connection.ts`, `drizzle.config.ts`) yield to any version already present.

**Two execution paths depending on which webapp template was used:**

| Mode | Webapp template | Backend work |
|------|-----------------|--------------|
| `--features db,auth` (default) | frontend-only (e.g. `0-origin`, `airlens-style`) | full graft: copy api/contracts/db, patch vite/tsconfig, auto-wire main.tsx/App.tsx, portal call, commit |
| `--template` | fullstack (ships `.backend-features.json` + pre-laid `api/`, `db/`, `contracts/`) | provision-only: read manifest, portal call, write `.env`, npm install, commit |

`--features` and `--template` are mutually exclusive. `--template` is selected automatically by the presence of `.backend-features.json` in the project — it reads the feature list from that manifest and skips all file copy/patch/wiring (the fullstack template already laid them out), doing portal provisioning + `.env` only.

### Worktree setup (run by subagents)

Use **swarm-workspace**'s `setup-local.sh`, passing this skill's prebuilt backend
`node_modules` (Hono/tRPC/Drizzle) as `NODE_MODULES_SRC`:

```bash
NODE_MODULES_SRC=/app/.agents/skills/backend-building-swarm/scripts/template/node_modules \
  bash /app/.agents/skills/swarm-workspace/scripts/setup-local.sh <branch> $HOME/app-<br