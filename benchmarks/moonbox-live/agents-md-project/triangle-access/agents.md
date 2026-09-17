# Multi-Agent Coordination Protocol
## Triangle Accessibility — Agent Architecture

**Version:** 2026-08-08-v3  
**Status:** Active — Iteration 0 Complete, Iteration 1 In Progress  
**Communication:** Git commits + shared docs + Redis pub/sub  

---

## Agent Registry

| ID | Name | Role | Owner | Priority | Status |
|----|------|------|-------|----------|--------|
| `FE-001` | **frontend-agent** | UI/UX, React components, accessibility audits, customer dashboard | Any | High | ✅ Iteration 0 Complete |
| `BE-001` | **backend-agent** | API design, database schema, security, Elysia endpoints | Any | High | 🟡 In Progress |
| `WP-001` | **wp-agent** | WordPress plugin dev, REST endpoints, headless config, KB integration | Any | High | ✅ Iteration 0 Complete |
| `PL-001` | **pipeline-agent** | Document processing, AI integration, queue workers, engines | Any | High | 🟡 In Progress |
| `MK-001` | **marketing-agent** | Content strategy, SEO, competitive analysis, social engine | Any | Medium | ✅ Iteration 0 Complete |
| `DO-001` | **devops-agent** | Deployment, monitoring, CI/CD, Docker, security hardening | Any | High | 🟡 In Progress |

---

## Iteration 0 — Foundation (COMPLETE)

| Task | Agent | Status | Deliverables |
|------|-------|--------|-------------|
| Competitor research | MK-001 | ✅ | Allyant, GrackleDocs, Equidox, 247accessible analyzed |
| State compliance matrix | MK-001 | ✅ | CO, CA, IL, MN, NY, TX, NC documented in docs/kb-seeds/ |
| Project scaffold | DO-001 | ✅ | Git repo, folder structure, Bun workspace |
| Iterative plan | DO-001 | ✅ | docs/plan.md with 7 iterations |
| Multi-agent protocol | DO-001 | ✅ | agents.md v3, task lifecycle, handoff templates |
| Bun + Elysia backend | BE-001 | ✅ | src/backend/index.ts — quote, upload, order, NIM proxy |
| NIM AI client | PL-001 | ✅ | src/backend/lib/nim-client.ts — preflight, alt-text, audit, marketing |
| NIM API routes | BE-001 | ✅ | src/backend/api/nim.ts — /ai/* endpoints |
| Next.js frontend | FE-001 | ✅ | src/frontend/ — layout, homepage, Tailwind v4 config |
| Quote calculator page | FE-001 | ✅ | src/frontend/app/quote/page.tsx — 3-step flow |
| Dashboard page | FE-001 | ✅ | src/frontend/app/dashboard/page.tsx — orders/files/team/settings |
| Upload page | FE-001 | ✅ | src/frontend/app/upload/page.tsx — drag-drop, multi-file, progress |
| Colorado state page | MK-001 | ✅ | src/frontend/app/state/colorado/page.tsx — HB21-1110 SEO landing |
| Competitor comparisons | MK-001 | ✅ | /compare/allyant, /compare/grackle, /compare/equidox |
| WordPress admin plugin | WP-001 | ✅ | triangle-admin.php — CPTs, REST API, dashboard, KB |
| KB seed articles | WP-001 | ✅ | Colorado HB21-1110, WCAG 2.1 AA, Section 508, PDF/UA |
| Docker Compose stack | DO-001 | ✅ | config/docker-compose.yml — WP, DB, Redis, API, Nginx |
| Nginx reverse proxy | DO-001 | ✅ | config/nginx.conf — 80/443, SSL, rate limiting, WP admin restricted |
| GitHub Actions CI/CD | DO-001 | ✅ | .github/workflows/ci.yml — test, lint, build, deploy |
| Secrets management | DO-001 | ✅ | .env.keys (primary), config/secrets/ (submodule backup) |
| Pre-commit hooks | DO-001 | ✅ | scripts/pre-commit-hook.sh — blocks secrets, API keys, PATs |
| Dev helper scripts | DO-001 | ✅ | push.sh, sync-submodules.sh, dev-start.sh, lint-fix.sh, test-all.sh, backup.sh |
| Porkbun analysis | DO-001 | ✅ | docs/porkbun_analysis.md — dedicated server recommended |
| WordPress plugin requirements | WP-001 | ✅ | docs/wordpress_plugin_requirements.md — 17 plugins, install script |
| External plugin guide | WP-001 | ✅ | docs/EXTERNAL_PLUGINS.md — MainWP recommended for admin control |
| Swarm workspace | DO-001 | ✅ | swarm-workspace.yml — agent registry, NIM config, coordination |

---

## Iteration 1 — Core API & Quote System (IN PROGRESS)

| Task | Agent | Status | Blockers |
|------|-------|--------|----------|
| PostgreSQL schema + Drizzle | BE-001 | 🟡 | None |
| Redis queue setup (BullMQ) | BE-001 | 🟡 | None |
| Stripe checkout integration | BE-001 | 🔴 | Need Stripe account |
| Clerk/Better Auth setup | BE-001 | 🔴 | Need Clerk account |
| File upload pre-signed URL | BE-001 | 🟡 | Need R2/S3 credentials |
| NIM API endpoint fix | PL-001 | 🟡 | Chat completions 404 — debugging |
| accesspdf submodule sync | PL-001 | 🔴 | Need submodule init |
| WordPress plugin install script | WP-001 | 🟡 | Need WP instance |
| Admin panel Next.js routes | FE-001 | 🔴 | Need auth system |
| Marketing content engine | MK-001 | 🔴 | Need NIM marketing endpoint stable |

---

## Agent Knowledge Base Access

All agents have read access to:
- `docs/plan.md` — Canonical roadmap (append-only)
- `docs/kb-seeds/` — Compliance guides, state laws, WCAG docs
- `docs/wordpress_plugin_requirements.md` — Plugin specs
- `docs/porkbun_analysis.md` — Hosting decisions
- `config/openapi/` — API contracts
- `agents.md` — This file (agent coordination)
- `.env.keys` — Primary secrets (local, gitignored, accessible to pseudo-admin)
- `config/secrets/.env.keys` — Backup secrets (submodule, for Andy/Chris sharing)

**Knowledge Base Integration:**
- WP-001 seeds KB articles into WordPress on activation
- FE-001 embeds KB content in frontend (React components fetching `/wp-json/triangle/v1/kb`)
- BE-001 serves KB via REST API with Redis caching
- MK-001 generates content from KB for marketing
- PL-001 uses KB compliance rules for validation pipelines

---

## Agent Communication Protocol

### 1. Shared State (Git + Docs)
All agents read/write to:
- `docs/plan.md` — Canonical roadmap. **Only append, never overwrite.**
- `agents.md` — This file. Agent status updates go here.
- `config/openapi/` — API contracts. All agents validate against these.
- `.env.keys.example` — Shared env template. Real secrets in `.env.keys` (never committed, accessible to pseudo-admin).
- `config/secrets/.env.keys` — Backup secrets for team sharing (submodule).

### 2. Task Assignment Format
Tasks are YAML files in `agents/tasks/`:

```yaml
# agents/tasks/FE-001-001.yaml
task_id: FE-001-001
agent: frontend-agent
priority: high
status: in_progress
dependencies:
  - task_id: BE-001-001
    status: completed
  - task_id: BE-001-002
    status: in_progress
objective: "Build customer-facing quote calculator with real-time NIM AI preflight"
deliverables:
  - path: src/frontend/components/quote-calculator.tsx
    type: component
    acceptance: WCAG 2.1 AA, mobile responsive, <100ms calc
  - path: src/frontend/app/page.tsx
    type: page
    acceptance: Hero + calculator above fold, Lighthouse 90+
  - path: tests/quote-calculator.test.ts
    type: test
    acceptance: 100% branch coverage
constraints:
  - "Use Shadcn/ui components only"
  - "Tailwind CSS v4 utility classes"
  - "No external chart libraries — use Recharts or CSS"
  - "Color palette: #0A2540, #00D4AA, #FF6B35, #F6F9FC"
notes: |
  Preflight data comes from BE-001-001 endpoint.
  If NIM is unavailable, show offline pricing with retry button.
  Reference docs/kb-seeds/wcag-2.1-aa-guide.md for accessibility requirements.
```

### 3. Status Update Format
Agents update their status via git commits:

```
[FE-001] feat: add quote calculator with NIM preflight
- Component: src/frontend/components/quote-calculator.tsx
- Tests: 12 passing, 0 failing
- Lighthouse: 94 performance, 100 accessibility
- Blocked by: BE-001-002 (upload endpoint not ready)
- Next: Integrate BE-001-002 when available
- KB used: docs/kb-seeds/wcag-2.1-aa-guide.md (contrast ratios)
```

### 4. Conflict Resolution
When two agents modify the same file:
1. **First commit wins** — second agent rebases
2. **API contracts are immutable** — negotiate in `config/openapi/`
3. **Database schema changes require BE-001 approval**
4. **UI changes require FE-001 + MK-001 alignment**
5. **KB content changes require WP-001 + MK-001 review**

### 5. Redis Pub/Sub (Real-time Coordination)
For urgent coordination (not routine commits):

```
Channel: triangle:agent:coordination
Messages:
  { "type": "blocker", "from": "FE-001", "to": "BE-001", "msg": "Upload endpoint 500s on PDF > 10MB" }
  { "type": "ready", "from": "BE-001", "task": "BE-001-002", "msg": "Upload endpoint deployed to staging" }
  { "type": "review", "from": "DO-001", "task": "FE-001-001", "msg": "Security scan found XSS in quote calculator" }
  { "type": "kb-update", "from": "WP-001", "article": "colorado-hb21-1110", "msg": "Updated with 2026 amendments" }
```

---

## Agent Specializations

### frontend-agent (FE-001)
**Scope:** Everything the customer sees + admin dashboard UI
**Tech:** Next.js 16, React 19, Tailwind v4, Shadcn/ui, Framer Motion
**Key Concerns:**
- WCAG 2.1 AA compliance (dogfooding)
- Core Web Vitals (LCP < 2.5s, CLS < 0.1)
- Mobile-first responsive design
- Dark mode support
- Real-time updates (WebSocket or SSE)
- KB article embedding via `/api/v1/kb`

**Deliverables:**
- Marketing pages (/, /about, /pricing, /compare)
- Customer dashboard (/dashboard, /orders, /files)
- Admin dashboard UI (/admin/* routes in Next.js)
- Quote calculator component
- File upload dropzone
- Order kanban board
- Analytics charts
- KB article viewer

**Interfaces:**
- Consumes: `BE-001` API, `WP-001` GraphQL, `docs/kb-seeds/`
- Produces: React components, page routes, test suites

**Iteration 0 Complete:**
- ✅ Homepage with hero, trust bar, quote calculator
- ✅ /quote — 3-step flow (upload → details → result with AI preflight)
- ✅ /dashboard — orders table, file cards, team tab, settings
- ✅ /upload — drag-drop, multi-file, progress bar, security badges
- ✅ /state/colorado — HB21-1110 SEO landing page
- ✅ /compare/allyant, /compare/grackle, /compare/equidox — competitor comparison tables

---

### backend-agent (BE-001)
**Scope:** All API endpoints, database, auth, payments, webhooks
**Tech:** Bun, Elysia, Drizzle ORM, PostgreSQL, Redis, Zod
**Key Concerns:**
- Type safety (TypeScript strict, Zod validation)
- Performance (< 100ms API response time)
- Security (JWT, rate limiting, input sanitization)
- Idempotency (all payment operations)
- Audit logging (every file access logged)
- KB article serving with Redis caching

**Deliverables:**
- REST API (`/api/v1/*`)
- GraphQL schema extensions (if needed)
- Database schema + migrations
- Auth middleware (Clerk/Better Auth integration)
- Stripe integration (subscriptions + usage billing)
- Webhook handlers (Stripe, GitHub, file processing)
- Rate limiting + DDoS protection
- KB API endpoints (`/api/v1/kb`, `/api/v1/kb/:slug`)

**Interfaces:**
- Consumes: `WP-001` REST API, `PL-001` processing queue, `docs/kb-seeds/`
- Produces: OpenAPI specs, database migrations, API clients

**Iteration 0 Complete:**
- ✅ Elysia scaffold with quote, upload, order, health endpoints
- ✅ NIM AI proxy routes (/ai/health, /ai/completion, /ai/preflight, /ai/alt-text, /ai/audit, /ai/marketing)
- ✅ Swagger docs at /swagger
- ✅ CORS, JWT middleware setup

**Iteration 1 In Progress:**
- 🟡 PostgreSQL + Drizzle schema
- 🟡 Redis BullMQ queue setup
- 🔴 Stripe checkout (need account)
- 🔴 Clerk auth (need account)

---

### wp-agent (WP-001)
**Scope:** WordPress headless setup, custom plugins, admin panel, KB management
**Tech:** PHP 8.3, WordPress 6.6+, WPGraphQL, ACF, Custom REST API
**Key Concerns:**
- No paid plugins (free/open source only)
- Fast admin dashboard (< 500ms TTFB)
- Knowledge base integration (seed + manage)
- Team notification routing (Andy/Chris)
- Custom REST endpoints for frontend
- KB article versioning and state tagging

**Deliverables:**
- `triangle-accessibility-api` plugin (custom REST endpoints)
- `triangle-accessibility-admin` plugin (admin dashboard + KB)
- `triangle-accessibility-kb-seeder` plugin (initial KB content from `docs/kb-seeds/`)
- WordPress theme (minimal, admin-focused)
- WPGraphQL configuration
- ACF field groups (JSON export)
- Plugin installation + configuration scripts
- KB taxonomy: `triangle_kb_category`, `triangle_kb_state`

**Interfaces:**
- Consumes: `BE-001` webhooks, `PL-001` processing results, `docs/kb-seeds/`
- Produces: REST API, GraphQL schema, admin UI, KB content

**Iteration 0 Complete:**
- ✅ triangle-admin.php — CPTs (orders, quotes, KB), REST API, admin menu, dashboard
- ✅ Admin CSS/JS — brand styling, dark mode, animations, API integration
- ✅ KB seed articles — Colorado HB21-1110, WCAG 2.1 AA, Section 508, PDF/UA
- ✅ WordPress plugin requirements doc — 17 plugins, install script
- ✅ External plugin guide — MainWP recommended for admin control

**Iteration 1 In Progress:**
- 🟡 WordPress install script (needs WP instance)
- 🔴 MainWP installation and configuration

---

### pipeline-agent (PL-001)
**Scope:** Document processing, AI integration, queue workers, engine management
**Tech:** Python, Bun workers, Redis BullMQ, Docker, Git submodules
**Key Concerns:**
- Git submodule sync (daily via PAT)
- Processing reliability (retry logic, dead letter queues)
- AI cost optimization (NIM free tier, Gemini fallback)
- Compliance validation (WCAG 2.1 AA, PDF/UA, Section 508)
- Virus scanning (ClamAV integration)
- KB compliance rules applied to output validation

**Deliverables:**
- `accesspdf` submodule integration (PDF remediation)
- Pandoc pipeline (DOCX/PPTX processing)
- NIM AI client (alt-text generation, preflight analysis)
- BullMQ job queue (Redis-based)
- Compliance validator (post-processing check against KB rules)
- Virus scanner (ClamAV wrapper)
- Engine health monitor (submodule status dashboard)
- KB rule engine: validate output against `docs/kb-seeds/` compliance standards

**Interfaces:**
- Consumes: `BE-001` job queue, `DO-001` Docker infrastructure, `docs/kb-seeds/`
- Produces: Remediated files, compliance reports, AI-generated metadata

**Iteration 0 Complete:**
- ✅ nim-client.ts — completion, preflight, alt-text, audit, marketing, health check functions
- ✅ nim.ts API routes — all /ai/* endpoints
- ✅ NIM API key tested (model listing works)

**Iteration 1 In Progress:**
- 🟡 NIM chat completions endpoint debugging (404 error — endpoint may need adjustment)
- 🔴 accesspdf submodule sync (needs GitHub PAT in environment)
- 🔴 Pandoc pipeline setup (needs DOCX/PPTX engine research)

---

### marketing-agent (MK-001)
**Scope:** Content strategy, SEO, competitive analysis, social media engine
**Tech:** Next.js pages, OpenAI/Gemini API, analytics APIs
**Key Concerns:**
- Mixture of Experts content system (5 personas)
- Competitor keyword conquest (Allyant, Grackle, Equidox, 247accessible)
- State law landing pages (SEO-optimized)
- Social media scheduling (LinkedIn, Twitter/X)
- Case study generation (automated from order data)
- KB content repurposing for marketing

**Deliverables:**
- Competitor comparison pages (/compare/allyant, /compare/grackle, /compare/equidox)
- State law landing pages (/state/colorado/hb21-1110, etc.)
- Content calendar (LinkedIn, Twitter, YouTube, TikTok)
- Case study templates (automated data pull)
- Review harvesting scripts (G2, Capterra, TrustRadius)
- SEO audit + keyword tracking
- KB content → marketing content pipeline

**Interfaces:**
- Consumes: `BE-001` order data (anonymized), `WP-001` KB content, `docs/kb-seeds/`
- Produces: Marketing pages, social posts, whitepapers, email campaigns

**Iteration 0 Complete:**
- ✅ Competitor analysis — Allyant, GrackleDocs, Equidox, 247accessible
- ✅ Competitor comparison pages — /compare/allyant, /compare/grackle, /compare/equidox
- ✅ Colorado state landing page — /state/colorado
- ✅ State compliance matrix — CO, CA, IL, MN, NY, TX, NC

**Iteration 1 In Progress:**
- 🔴 Remaining state landing pages (CA, IL, MN, NY, TX)
- 🔴 Social media content engine (needs NIM marketing endpoint stable)
- 🔴 Case study automation (needs order data pipeline)

---

### devops-agent (DO-001)
**Scope:** Deployment, monitoring, CI/CD, security, infrastructure
**Tech:** Docker, GitHub Actions, Vercel, Cloudflare, Sentry, LogRocket
**Key Concerns:**
- Zero-downtime deployments
- Secret rotation automation
- Infrastructure as code (Terraform/Pulumi)
- Security hardening (WAF, CSP, rate limiting)
- Cost optimization (free tier maximization)
- KB backup and versioning

**Deliverables:**
- Docker Compose (WordPress + DB + Redis)
- GitHub Actions workflows (test, build, deploy)
- Vercel deployment config (frontend)
- Cloudflare Workers config (API edge caching)
- Terraform modules (AWS R2, S3, Lambda)
- Monitoring dashboards (Sentry, UptimeRobot)
- Security scan automation (OWASP ZAP, Trivy)
- Backup automation (DB + files + Git repos + KB content)
- Reverse proxy config (80/443, Nginx or Caddy)

**Interfaces:**
- Consumes: All agent deliverables
- Produces: Infrastructure, CI/CD pipelines, monitoring

**Iteration 0 Complete:**
- ✅ Docker Compose — WP, MySQL, PostgreSQL, Redis, API, Nginx
- ✅ Nginx reverse proxy — 80/443, SSL, rate limiting, WP admin IP-restricted
- ✅ GitHub Actions CI/CD — test, lint, typecheck, build, deploy
- ✅ Secrets management — .env.keys (primary), config/secrets/ (submodule backup)
- ✅ Pre-commit hooks — blocks secrets, API keys, PATs
- ✅ Dev helper scripts — push.sh, sync-submodules.sh, dev-start.sh, lint-fix.sh, test-all.sh, backup.sh
- ✅ Porkbun analysis — dedicated server recommended
- ✅ Swarm workspace — agent registry, NIM config, coordination

**Iteration 1 In Progress:**
- 🔴 Deploy to Andy's dedicated server (needs server access)
- 🔴 SSL certificates (Let's Encrypt)
- 🔴 DNS configuration (Porkbun → server IP)
- 🔴 Monitoring setup (Sentry, UptimeRobot)

---

## Agent Task Lifecycle

```
1. PLAN     → Task defined in agents/tasks/{agent-id}-{seq}.yaml
2. CLAIM    → Agent updates status to "in_progress" in agents.md
3. DEV      → Agent works in their src/ directory, commits frequently
4. TEST     → Agent runs tests, updates acceptance criteria
5. REVIEW   → Cross-agent review (minimum 1 other agent)
6. MERGE    → PR merged to main (squash or rebase)
7. DEPLOY   → DO-001 deploys to staging → production
8. MONITOR  → All agents monitor for 24h post-deploy
```

---

## Current Sprint: Iteration 1 — Core API & Quote System

| Task | Agent | Status | Blockers |
|------|-------|--------|----------|
| PostgreSQL schema + Drizzle ORM | BE-001 | 🟡 | None |
| Redis BullMQ queue | BE-001 | 🟡 | None |
| Stripe checkout integration | BE-001 | 🔴 | Stripe account |
| Clerk/Better Auth setup | BE-001 | 🔴 | Clerk account |
| File upload pre-signed URL (R2/S3) | BE-001 | 🟡 | R2 credentials |
| NIM API endpoint fix | PL-001 | 🟡 | Debugging 404 |
| accesspdf submodule sync | PL-001 | 🔴 | GitHub PAT env |
| WordPress plugin install | WP-001 | 🟡 | WP instance |
| Admin panel Next.js routes | FE-001 | 🔴 | Auth system |
| Remaining state landing pages | MK-001 | 🔴 | NIM stable |
| Deploy to dedicated server | DO-001 | 🔴 | Server access |

---

## Agent Handoff Template

When an agent completes work that another agent depends on:

```markdown
## Handoff: {from-agent} → {to-agent}
**Task:** {task-id}
**Date:** {YYYY-MM-DD}

### Delivered
- [ ] File: `{path}` — Description
- [ ] API: `{endpoint}` — Schema + example response
- [ ] Test: `{path}` — Coverage %
- [ ] KB: `{article}` — Updated/created

### Known Issues
- {issue} — {workaround or fix needed}

### Next Steps for {to-agent}
1. {step}
2. {step}

### Knowledge Base References
- docs/kb-seeds/{article}.md — Relevant compliance rules
- docs/wordpress_plugin_requirements.md — Plugin specs

### Contact
- Slack/Discord: #{channel}
- GitHub: @{username}
```

---

## Emergency Escalation

If an agent is blocked for > 4 hours:
1. Post in `triangle:agent:coordination` Redis channel
2. Tag `@all` in commit message
3. If critical path, DO-001 can override and reassign
4. **KB emergency:** If compliance rules change, WP-001 immediately updates `docs/kb-seeds/` and notifies all agents

---

## Automation Rules (DO-001 Enforced)

### Git Push (Every Commit > 3 Times)
- **Rule:** If an agent pushes > 3 times in a session, use `./scripts/push.sh "message"`
- **Why:** Reduces manual steps, ensures consistency
- **Enforcement:** DO-001 monitors git logs, reminds agents

### Submodule Sync (Weekly)
- **Rule:** Run `./scripts/sync-submodules.sh` every Monday
- **Why:** Keeps remediation engines up to date
- **Enforcement:** GitHub Actions cron job + DO-001 reminder

### Dev Environment Start (Daily)
- **Rule:** Use `./scripts/dev-start.sh` to start all services
- **Why:** Consistent environment, loads .env.keys automatically
- **Enforcement:** Documented in README, DO-001 verifies

### Lint & Test (Before Every Push)
- **Rule:** Run `./scripts/lint-fix.sh` and `./scripts/test-all.sh` before push
- **Why:** Prevents broken code in main
- **Enforcement:** Pre-commit hook (installed via `./scripts/install-hooks.sh`)

### Backup (Daily)
- **Rule:** Run `./scripts/backup.sh daily` via cron
- **Why:** Protects against data loss
- **Enforcement:** DO-001 configures cron, monitors backup integrity

---

## Knowledge Base Update Protocol

When compliance rules change (e.g., new state law, WCAG update):

1. **WP-001** updates `docs/kb-seeds/{article}.md`
2. **WP-001** commits: `docs: update KB — {state} {law} {date}`
3. **WP-001** pushes via `./scripts/push.sh`
4. **WP-001** posts to Redis: `{ "type": "kb-update", "article": "{slug}" }`
5. **All agents** pull latest KB on next task start
6. **PL-001** updates validation rules in processing pipeline
7. **MK-001** updates marketing content if affected
8. **FE-001** updates frontend if user-facing changes

---

---

## Sandbox Persistence Protocol (CRITICAL — Read This)

### The Problem
This environment is a **K8s sandbox**. `/mnt/agents/output` is a network drive (`drive9`) that gets cleaned/reset by the orchestrator between sessions. **`.git` directories are NOT guaranteed to persist.** Do not treat local git state as durable.

**What this means:**
- `git init`, `git commit`, `git push` in the sandbox are ephemeral
- `.git` dirs may disappear between sessions without warning
- `experimental-crisis` already lost its `.git` twice
- `git clone` and `git push` from the sandbox often **timeout** (network throttled)

### The Correct Pattern

**1. GitHub is the single source of truth.**
Local work is temporary. Always push to GitHub before ending a session. If `.git` vanishes, re-clone from GitHub.

**2. Use `SESSION_RECOVER.sh` at the start of every session.**
```bash
bash /mnt/agents/output/SESSION_RECOVER.sh
```
This script:
- Checks if `.git` exists in each repo
- If yes → `git pull` latest from GitHub
- If no → `git clone --depth=1` fresh from GitHub
- Re-installs hooks automatically

**3. If `git clone`/`git push` timeout in the sandbox, do NOT retry.**
The network is throttled. Instead:
```bash
# In sandbox: commit locally, save files
git add -A
git commit -m "wip: ..."
# DO NOT push from here — it will hang

# On your local machine:
git clone https://github.com/toxicwind/{repo}.git
cd {repo}
# Copy files from sandbox (scp, rsync, or manual)
git add -A && git commit -m "sync from sandbox" && git push
```

**4. For repos that don't exist on GitHub yet:**
```bash
# In sandbox: create the repo via API first
curl -X POST -H "Authorization: token $GITHUB_PAT" \
  -d '{"name":"new-repo","private":true}' \
  https://api.github.com/user/repos

# Then clone it back to get a proper .git
git clone --depth=1 https://${GITHUB_PAT}@github.com/toxicwind/new-repo.git
```

**5. Never run `git init` + `git commit` + `git push` as separate tool calls.**
That burns tool budget for no durable result. Instead:
- Do all file work in Python/shell
- One `git add -A && git commit` at the end
- Push from your local machine, not the sandbox

**6. If `.git` disappears mid-session:**
```bash
# Don't panic. Check if the remote repo exists:
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: token $GITHUB_PAT" \
  https://api.github.com/repos/toxicwind/{repo}

# If 200: clone fresh
rm -rf /mnt/agents/output/{repo}
git clone --depth=1 https://${GITHUB_PAT}@github.com/toxicwind/{repo}.git \
  /mnt/agents/output/{repo}

# If 404: repo doesn't exist remotely. Re-init and commit locally.
# Push from your local machine later.
```

### Anti-Patterns (Don't Do This)

| Anti-Pattern | Why It Fails |
|--------------|-------------|
| `git init` → work → `git commit` → session ends | `.git` may be gone next session |
| Retry `git push` 3x after timeout | Wastes tool calls, never works |
| Assume `.git` persists because it survived once | K8s cleans unpredictably |
| Commit secrets because "I'll fix it later" | Secrets in git history = permanent |
| Use `git remote` without PAT in URL | Auth fails silently |

### Files That Persist (Reliably)

| Location | Persistence | Use For |
|----------|-------------|---------|
| `/mnt/agents/output/` | Network drive, survives sessions | Source code, configs |
| `/mnt/agents/output/reports/` | Same | Audit data, CSVs, JSON |
| `/mnt/agents/temp/` | Session-only | Temporary downloads |
| `/tmp/` | Session-only | Build artifacts |
| `.git/` | **NOT persistent** | Nothing — use GitHub |

### Recovery Checklist

When `.git` disappears:
1. [ ] Run `bash /mnt/agents/output/SESSION_RECOVER.sh`
2. [ ] If clone times out, download files via `zip` or `scp` to local machine
3. [ ] Push from local machine with proper PAT
4. [ ] Re-install hooks: `chmod +x .git/hooks/pre-commit .git/hooks/pre-push`
5. [ ] Verify: `git log --oneline -3` shows expected history

---

*This document is append-only. Status updates are inline edits. No deletions.*
*For knowledge base content, see `docs/kb-seeds/`.*
*For technical architecture, see `docs/plan.md`.*
*For hosting decisions, see `docs/porkbun_analysis.md`.*
