---
name: backend-building
description: Backend building that grafts tRPC + Drizzle ORM + Hono onto an existing webapp-building frontend. Supports incremental features (db, auth). Use when the user needs a backend, API, database, server, authentication, or wants to add tRPC/Drizzle to their webapp-building project. Requires webapp-building first.
---

# Backend Building

**Stack**: tRPC + Drizzle ORM + Hono + MySQL + OAuth 2.0

A backend-only skill that grafts onto an existing `webapp-building` project. It adds `api/`, `contracts/` directories and optionally `db/` — but **never replaces or modifies** existing frontend files.

**Prerequisite**: An existing project created by `webapp-building`.

## Features

Features can be installed incrementally. Base infrastructure (Hono server, tRPC, contracts) is always installed automatically on first run.

| Feature | What it provides | Dependencies |
|---------|-----------------|--------------|
| `db` | Drizzle ORM + MySQL — adds `db/`, `api/queries/connection.ts`, `drizzle.config.ts` | — |
| `auth` | Kimi OAuth + user management — adds `api/kimi/`, Login page, useAuth, AuthLayout | requires `db` (auto-included) |

Default: `init.sh "App"` with no `--features` → defaults to `auth` (= db + auth), preserving backward compat.

## Workflows

**Frontend-first** (recommended when UI is already built):

1. `webapp-building` init → develop UI pages and components
2. `backend-building` graft (this skill) — auto-wires tRPC providers and routes
3. Verify with `npm run check`, then add tRPC routers, database tables, wire frontend to API

**Full-stack from scratch** (recommended when backend is needed immediately):

1. `webapp-building` init → immediately graft `backend-building`
2. Verify with `npm run check`
3. Develop frontend and backend together

**Incremental features** (add capabilities over time):

1. Start with `--features db` for database only
2. Later add auth: `init.sh "App" --features auth`

## Quick Start

### 1. Initialize Frontend First (webapp-building)

```bash
bash /app/.agents/skills/webapp-building/scripts/init-webapp.sh "My App"
cd /mnt/agents/output/app
```

### 2. Graft Backend

```bash
# Full stack with auth (default, same as before):
bash /app/.agents/skills/backend-building/scripts/init.sh "My App"

# Database only (no auth):
bash /app/.agents/skills/backend-building/scripts/init.sh "My App" --features db

# Add auth later:
bash /app/.agents/skills/backend-building/scripts/init.sh "My App" --features auth

```

**What this does (base, always on first run):**

- Copies `api/`, `contracts/` into the project
- Patches `vite.config.ts` in-place (adds `@contracts` alias, `envDir`, `build.outDir`)
- Adds `tsconfig.server.json` and merges `@contracts/*` path into existing tsconfigs
- Merges `package.json` (adds backend deps and scripts)
- Generates `.env` with portal credentials
- Runs `npm install`

**Additional per feature:**

- **db**: Adds `db/` directory, `drizzle.config.ts`, database connection, `DATABASE_URL` env var, and `db/seed.ts` (scaffold for seeding — run with `npx tsx db/seed.ts`). **Do not overwrite** the generated `api/queries/connection.ts`, `drizzle.config.ts`, or `.env` — they are complete and correct. Only add your tables to `db/schema.ts`
- **auth**: Adds `api/kimi/`, auth router, client patches (Login, useAuth, AuthLayout, TRPCProvider), auto-wires Login/NotFound routes into `App.tsx`

### 3. Verify Auto-Wiring (see below)

### 4. Database Setup (if db or auth feature installed)

```bash
npm run db:push        # sync schema to database (recommended for development)
```

### 5. Development

```bash
npm run dev
```

Start development server with HMR at `http://localhost:3000`

## Post-Init Wiring

On first run, `init.sh` auto-wires `TRPCProvider` into `src/main.tsx`. When `auth` feature is installed, it also adds Login/NotFound routes to `src/App.tsx`. Check the init output:

- **"Auto-wired"** — no action needed, proceed to verification
- **"Wiring required"** — complete the listed steps manually (see [Post-Init Wiring](docs/Post-Init-Wiring.md) for details)

If manual wiring is needed, it typically means:

1. Add `import { TRPCProvider } from "@/providers/trpc"` to `src/main.tsx`
2. Wrap the content inside `<BrowserRouter>` with `<TRPCProvider>`
3. Add Login and NotFound routes to `src/App.tsx`

### Verification

After init (and manual wiring if needed), verify everything works:

1. Run `npm run check` — must pass with zero type errors
2. Run `npm run dev` — server should start at http://localhost:3000
3. If any step fails, read the error and fix before proceeding

## Common Commands

| Command              | Description                                                | Requires |
| -------------------- | ---------------------------------------------------------- | -------- |
| `npm run dev`        | Start development server with HMR at http://localhost:3000 | base |
| `npm run build`      | Build for production (outputs to dist/)         