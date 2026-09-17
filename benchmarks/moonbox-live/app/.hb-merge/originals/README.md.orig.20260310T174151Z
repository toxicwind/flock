<<<<<<< HEAD
# 🧪 EFFUSION LABS | HYPERBRUT CI ENGINE
> **VERSION: 2026.1.0** | **STANCE: CONSTRAINED_CI_MASTERY**

---

## 🟥 LIVE REPO BREAKDOWN (3X NON-BASELINE)

### 1. THE BUILD STACK [STATUS: OPTIMIZED]
Effusion Labs is a high-performance Eleventy-driven site engineered for **Hypebrut** aesthetics and constrained environments. The stack is ultra-modern, leveraging bleeding-edge versions of the core web ecosystem.

*   **CORE:** Eleventy 3.0 + Vite 7.0 + Tailwind 4.0
*   **LOGIC:** Node.js ≥ 22.19 (ESM Only)
*   **UI:** daisyUI 5.0 (Custom Hypebrut Tokens)
*   **BROWSER:** Chromium-driven policy targeting system binaries (Puppeteer/Playwright).

### 2. WHERE WE ARE AT [NETWORK_GATE: ACTIVE]
We have successfully implemented a "Network Contract" for CI, ensuring deterministic builds even in hostile or air-gapped environments.

| LAYER | STATUS | COMPONENT | ROLE |
| :--- | :--- | :--- | :--- |
| **Site Build** | 🟢 STABLE | Eleventy 3.0 | Static site generation with Vite hydration. |
| **Tooling** | 🟢 ACTIVE | `tools/` | Chromium resolvers and LV Images pipeline. |
| **CI Gate** | 🟢 HARDENED | `ci.yml` | Three-stage lint/test/build with offline shims. |
| **MCP Matrix** | 🟡 INTEGRATED | `mcp-stack/` | Gateway for AGENT-based interrogation. |
| **Shell Shims** | 🟢 ACTIVE | `bin/bin/` | Deterministic CLI wrappers (rg, fd, curl). |

### 3. PROTOCOL: CHROMIUM ISOLATION
Effusion Labs rejects the uncertainty of CDN-fetched browsers. All tooling (`Puppeteer`, `Playwright`) is strictly mapped to the system Chromium binary.
*   **Resolution:** `tools/resolve-chromium.mjs`
*   **Gatekeeper:** `bin/chromium` shim.
*   **Validation:** `tools/check-chromium.mjs` (Run before every test cycle).

---

## 🚀 STRATEGIC WORKFLOWS

### The "Quality Gate"
```bash
npm run check  # Doctor -> Quality Check -> Integration Tests
```

### LV Images Pipeline (Sync/Crawl)
```bash
npm run lv-images:sync  # Refresh + Bundle + Verify
```

### CI-Safe Build
```bash
npm run build:ci  # Production build with network contract enforcement
```

---

## 📂 ARCHITECTURAL HIERARCHY
*   **/src/content**: Markdown & Nunjucks primary source.
*   **/tools**: Build diagnostics and Chromium orchestration.
*   **/bin/bin**: The repository's "Nervous System" (Shims).
*   **/mcp-stack**: The gateway to Chronos-Forge awareness.

---
*Unified Effusion Labs Framework | Optimized for Autonomous Synthesis.*
=======
# Effusion Labs Digital Garden

Effusion Labs is a long‑form digital garden and studio powered by Eleventy, Nunjucks and Tailwind CSS. It serves as a structured space for developing ideas, capturing research and publishing a static site.

## Badges

[![License: ISC](https://img.shields.io/badge/license-ISC-blue.svg)](./LICENSE)

## Table of Contents

- [Overview](#overview)
- [Features / Capabilities](#features--capabilities)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Testing](#testing)
- [Web Ingestion Helper](#web-ingestion-helper)
- [Project Layout](#project-layout)
- [Deployment / Release](#deployment--release)
- [Contributing](#contributing)
- [License](#license)
- [Links](#links)

## Overview

This repository contains the source for the Effusion Labs site. The build pipeline combines Eleventy for static generation, Nunjucks templates for layout, and Tailwind CSS (with daisyUI) for styling. Markdown files under `src/content` provide the primary content. The project targets practitioners who want a reproducible digital garden with bidirectional links, a graph view and containerised deployment.

The repository is intentionally self‑describing. Configuration is expressed as code, tests run without network access and every external reference is captured for provenance. Publishing involves compiling Markdown and assets into a static directory that can be served by any HTTP host or bundled into a container image.

Content is organised into **Sparks**, **Concepts**, **Projects** and **Meta** areas. Documents can interlink and evolve over time, turning transient notes into durable knowledge while remaining easy to publish.

## Features / Capabilities

- **Eleventy static site** with configurable collections for Sparks, Concepts, Projects and Meta documents, generated via the shared register module and constants【F:lib/eleventy/register.js†L33-L38】【F:lib/constants.js†L7-L13】
- **Nunjucks layout** with an accessible dark/light theme toggle (defaulting to dark) driven by CSS variables, skip navigation link and meta sidebar for document metadata【F:src/_includes/layout.njk†L1-L37】【F:src/_includes/header.njk†L20-L27】
- **Tailwind CSS v4** configured through PostCSS, extended with custom colours and fonts, and wired to theme tokens via daisyUI【F:tailwind.config.cjs†L1-L43】【F:postcss.config.cjs†L1-L5】
- **Bidirectional linking** using `@photogabble/eleventy-plugin-interlinker`, producing annotated `<a class="interlink">` elements for internal references【F:lib/plugins.js†L1-L26】
- **Syntax highlighting** via `@11ty/eleventy-plugin-syntaxhighlight` and Prism themes loaded through the Tailwind entry file【F:lib/plugins.js†L27-L31】【F:src/styles/app.tailwind.css†L4-L5】
- **Responsive image transform**: `@11ty/eleventy-img` generates AVIF, WebP and original formats at multiple widths with lazy‑loading and async decoding attributes【F:lib/eleventy/register.js†L40-L52】
- **Interactive concept map** built with `vis-network`, exposing collections as a node‑edge graph at `/map/` for exploratory browsing【F:src/map.njk†L38-L121】
- **Webpage ingestion helper** providing both an Eleventy filter and a CLI to convert external pages to Markdown using Readability.js and Turndown【F:lib/filters.js†L1-L5】【F:lib/webpageToMarkdown.js†L1-L26】
- **PostCSS pipeline** that compiles `src/styles/app.tailwind.css` on each build and copies static assets through to `_site/`【F:lib/eleventy/register.js†L69-L72】
- **Accessible baseline** including skip‑link, semantic landmarks and footnote enhancements for improved keyboard navigation and readability【F:src/_includes/layout.njk†L33-L75】【F:src/styles/app.tailwind.css†L12-L38】

## Quickstart

### Prerequisites

- Node.js ≥20【F:package.json†L12-L13】
- npm (bundled with Node)

### Clone and Install

```bash
git clone https://github.com/effusion-labs/effusion-labs.git
cd effusion-labs
npm install
```

### Local Development

```bash
npm run dev
```

### Production Build

```bash
npm run build
```

### Run Tests

```bash
npm test
```

### Utility Scripts

```bash
npm run web2md -- <URL>  # fetch a web page, output Markdown and sha256 hash
npm run docs:archive     # capture vendor docs via web2md
npm run docs:reindex     # rebuild vendor docs index
npm run docs:validate    # verify hashes
```

The `dev` command watches templates, Markdown and styles, recompiling Tailwind through PostCSS before each serve cycle and serving `_site/` via BrowserSync. The `build` command performs a one‑off production build. Tests are hermetic and execute without internet access. The `web2md` command is described in detail below.

No lint or format scripts are defined.

## Configuration

- **Content directories**: Markdown lives under `src/content/{sparks,concepts,projects,meta}`【F:lib/constants.js†L7-L13】
- **Data files**: `src/_data/` holds global data such as navigation links【F:src/_data/nav.js†L1-L11】
- **Includes**: Nunjucks layouts and partials reside in `src/_includes/`
- **Env vars**:
  - `CASSETTE_DIR` – path to snapshot vault (`docs/cassettes/` by default)
  - `API_TWIN_DIR` – path to API twin stubs (`tools/api-twin/` by default)

Setting these variables allows custom storage locations for captures or twins when running tests in specialised environments. All other configuration resides in the `lib/` directory as plain JavaScript modules.

## Testing

`npm test` invokes Node’s built‑in test runner and executes all files under `test/`. The suite mixes unit tests for utility functions with integration tests that assert build outputs and runtime behaviour. Integration tests that exercise network calls use the **Live‑Capture‑Lock** policy:

- **Snapshot vault**: Recorded HTTP interactions are stored under `docs/cassettes/`【9ad1e7†L1-L2】
- **Creating captures**: run the relevant tests with network access; responses are saved as fixtures for replay
- **Replay**: PR CI replays snapshots and **fails closed** if a test attempts live network access
- **API twin**: when live capture is unsafe or unavailable, stub the endpoint under `tools/api-twin/` and point tests to the twin【44f46f†L1-L2】
- **Idempotency**: live probes must be repeatable and safe; destructive flows are simulated via the twin

Snapshots are deterministic: headers and bodies are stored alongside SHA256 hashes. Any attempt to mutate the snapshot store during CI causes the build to fail, ensuring reproducibility. Developers should refresh snapshots only when contract drift breaks replay, committing both the updated fixture and the rationale in the decision log. A new test validates the CLI helper, ensuring the emitted hash matches the Markdown content【F:test/web2md.cli.test.mjs†L1-L29】.

## Web Ingestion Helper

`webpageToMarkdown` converts remote pages into Markdown using `@mozilla/readability` to isolate the article body and `turndown` to convert HTML into Markdown. It powers both an Eleventy filter and the `web2md` CLI:

```bash
npm run web2md -- https://example.com/article > article.md
```

The CLI prints the normalized Markdown followed by a `sha256:` line containing the content hash, enabling reproducible references and easy provenance recording【F:webpage-to-markdown.js†L1-L19】. Redirect stdout to a file to capture the article and record the hash alongside other research notes.

### Outbound Proxy

`web2md` and `search2serp` honor these environment variables for outbound HTTPS proxying:

```
OUTBOUND_PROXY_ENABLED=0|1
OUTBOUND_PROXY_URL=host:port
OUTBOUND_PROXY_USER=...
OUTBOUND_PROXY_PASS=...
OUTBOUND_PROXY_NO_PROXY=domain[,domain]
```

CLI flags `--proxy`, `--no-proxy`, and `--no-proxy-hosts "host,host"` override enablement and bypass lists but never expose credentials.

Within templates, the filter can ingest content on build:

```njk
{{ "https://example.com/article" | webpageToMarkdown }}
```

## Project Layout

```
.
├── .eleventy.js               # Eleventy configuration entry
├── .github/workflows/deploy.yml
├── .portainer/                # Dockerfile and nginx.conf for deployment
├── docs/
│   ├── cassettes/             # Snapshot vault for recorded HTTP interactions
│   └── knowledge/             # Decision log, sources and research snapshots
├── lib/                       # Configuration, plugins, filters, utilities
├── src/
│   ├── _data/                 # Global data files
│   ├── _includes/             # Nunjucks layouts and partials
│   ├── assets/                # Static assets (copied through)
│   ├── content/               # Markdown content grouped by area
│   ├── scripts/               # Client-side JavaScript
│   └── styles/                # Tailwind entry points
├── test/                      # Node.js test suite
├── tools/
│   └── api-twin/              # Placeholder for API stubs used during offline tests
└── webpage-to-markdown.js     # CLI for web ingestion
```

## Deployment / Release

The project builds to static files in `_site/`. A GitHub Actions workflow installs dependencies, runs tests, builds the site and produces an Nginx image pushed to GitHub Container Registry. The container embeds the generated `_site/` output and a tailored `nginx.conf`. Successful pushes to `main` trigger the pipeline and a Portainer webhook redeploys the container on the target host【F:.github/workflows/deploy.yml†L1-L61】【F:.portainer/Dockerfile†L1-L24】.

Local deployment can be tested with:

```bash
docker build -t effusion-labs . -f .portainer/Dockerfile
docker run --rm -p 8080:80 effusion-labs
```

The running container serves the static site with caching headers and an SPA fallback defined in `.portainer/nginx.conf`.

## Contributing

1. Fork the repository and create a local clone.
2. Install dependencies with `npm install`.
3. Create feature branches that keep experimental work behind flags.
4. Update or add tests alongside code changes; record any new external captures in `docs/knowledge/` and commit snapshots under `docs/cassettes/`.
5. Run `npm test` to ensure the suite passes and snapshots are replayed without network access.
6. Submit a pull request describing your changes, snapshot updates and any assumptions.

## License

This project is licensed under the [ISC License](./LICENSE)【F:LICENSE†L1-L11】

## Links

- [docs/knowledge/](./docs/knowledge/) – decision history and source captures
- [tools/api-twin/](./tools/api-twin/) – API twin stub location
>>>>>>> broken/codex/add-dark-mode-as-default-with-light-mode-option
