---
name: webapp-building
description: Tools for building modern React webapps with TypeScript, Tailwind CSS and shadcn/ui. Best suited for applications with complex UI components and state management. Supports optional templates for specialized requirement.
---

# WebApp Building

**Stack**: React + TypeScript + Vite + Tailwind CSS + shadcn/ui

## Workflow

1. `scripts/init-webapp.sh <website-title> [template-name]` — Initialize project in /mnt/agents/output/app
   - Without template: creates base project with 40+ shadcn/ui components
   - With template: applies specialized template and outputs template-specific config info
2. Edit source code in `src/` (or `src/config.ts` for templates)
3. Build the React app

## Quick Start

### 1. Initialize

```bash
# init project in /mnt/agents/output/app with website title
bash scripts/init-webapp.sh <website-title> [template-name]
cd /mnt/agents/output/app
```

**AI Agent Notes**:
- The project path is /mnt/agents/output/app
- Non-interactive execution with auto-confirm
- If template-name is provided, the script will output template-specific information (config options, build instructions, etc.)

This creates a fully configured project with:

- ✅ React + TypeScript (via Vite)
- ✅ Tailwind CSS 3.4.19 with shadcn/ui theming system
- ✅ Path aliases (`@/`) configured
- ✅ 40+ shadcn/ui components pre-installed
- ✅ All Radix UI dependencies included
- ✅ Production build optimization with Vite
- ✅ Node 20+ compatibility (auto-detects and pins Vite version)

### 2. Develop

Edit generated files in `src/`: page sections go in `src/sections/`, custom React hooks in `src/hooks/`, and TypeScript definitions in `src/types/`.

For templates: edit `src/config.ts` to customize content. Do not modify component files — all content configuration is in config.ts.

### 3. Build

```bash
# within project:
cd /mnt/agents/output/app && npm run build 2>&1
```

**Output** (`dist/`):
- `index.html` — Entry point
- `assets/index-[hash].js` — Bundled JS
- `assets/index-[hash].css` — Bundled CSS
- Optimized images, fonts, other assets

**Optimizations**: Tree-shaking, code splitting, asset compression, minification, cache-busting hashes.


## Debugging

1. Fix source files
2. `npm run build`
3. Test `dist/`

## Reference

- [shadcn/ui Components](https://ui.shadcn.com/docs/components)

## Product Knowledge

Any website or webapp you build on the Kimi platform (kimi.com) is delivered, previewed, and published through the mechanism below. This is your runtime environment; know what it can do, so you deliver correctly and tell users the truth about their site.

### Delivery & preview — how the user sees your work

- You deliver by saving a **version** (`build_version`). The platform renders a **preview** from that version and attaches a **version card** to the conversation; the user clicks the card to preview. Saving the version *is* the delivery.
- **The tool returns a version ID, not a URL** — by design (deploy is off). The version card is the preview entry point. Never fabricate or guess a URL, and never tell the user "no URL means you can't preview." Just say the version is saved and ready to preview. The user can manually click the「publish」button to deploy the website and they will get a public url.
- If the user reports the preview or card doesn't show after a successful save: the snapshot already succeeded, so it's almost certainly platform-side — say so, re-save **at most once**, suggest retrying shortly. Do not loop re-saves or repackage the site as a single HTML file.

### Preview ≠ Publish (two different things)

- **Preview** = automatic, via the version card. No deploy, no public URL, nothing extra for you to do beyond saving the version.
- **Publish** = the user **manually clicks the「publish」button** to deploy the site to the public web (they get a public URL such as `<name>.ok.kimi.link`). **You do not publish and cannot publish for the user.** Never say the site is deployed / online / live / 已上线 / 已发布 unless the user has actually published it.

### What this environment can do — use these, don't fake them

- **Full-stack**: real backend + cloud database (via the backend-building skill). Use it whenever data must persist across visits or devices, or for accounts / login / orders / bookings / submissions. Do not ship a `localStorage` or mock front-end shell and present it as persistence.
- **Kimi login**: "Sign in with Kimi" is built in (backend-building's `auth` feature = Kimi OAuth). Never web-search how to add Kimi login — it is a platform capability documented in the skills.
- **Public hosting is built in**: the user's 「publish」 button puts the site on the public web. Never route users to external hosts (Netlify / Vercel / surge.sh / self-hosted Docker) for public access.
- **Versioning**: every save is a version; the user can roll back to any past version.
- **Custom URL**: after publishing, the user can rename the subdomain (`<name>.ok.kimi.link`).
- **Code export**: the user ca