# Build Output Weirdness Audit — 2026-03-12

This document consolidates the weirdness currently visible in the Bun + Eleventy build output so we can fix it deliberately instead of chasing noise.

## Scope

Observed from a successful local run of:

- `bun run build`

Observed output included:

- CSS optimizer warnings
- Node/ESM warnings
- runtime data fallback warnings
- stray debug logs
- unexpected generated routes
- suspicious duplicate config/layout structures

## Executive summary

The build now **completes successfully**, but the output is still noisy for real reasons:

1. **Some warnings are genuine configuration or source-structure problems**.
2. **Some logs are intentional fallback behavior but too noisy for normal production builds**.
3. **Some generated output is clearly wrong**, especially layout pages and the broken feed route.
4. **The repo contains duplicate Eleventy/layout structures**, which makes the build harder to reason about and easier to break.

---

## Line-by-line weirdness ledger

| Symptom in build output | Classification | Evidence | Likely cause | Impact | Recommended next move |
|---|---|---|---|---|---|
| `Found 4 warnings while optimizing generated CSS` with invalid pseudo-classes like `:first-childu003eu0026` | Real bug / CSS pipeline issue | Build output warnings during `bun run build` | Tailwind/daisyUI generated selectors are getting escaped into malformed pseudo-classes during CSS optimization | Build still passes, but CSS pipeline is not clean and could produce broken edge-case selectors | Trace the exact utility/plugin source and either remove the bad utility pattern or isolate the minifier/plugin step producing the broken selector |
| `[MODULE_TYPELESS_PACKAGE_JSON]` for `src/index.11tydata.js` | Real warning / module-format mismatch | Build output warning from Node | `src/index.11tydata.js` uses ESM syntax, but root `package.json` does not declare `"type": "module"` | Extra reparsing overhead and build noise; format expectations are muddy | Decide explicitly: either convert affected files to CommonJS or move repo/package runtime to explicit ESM where safe |
| `[cannabis] API fetch failed ... Using fallback data.` | Intentional fallback, but noisy and potentially masking drift | `src/_data/cannabis.js` | Build-time data source defaults to `http://localhost:8000/api/cannabis`, which is absent in normal local builds | Build succeeds but data is synthetic/randomized fallback data; can hide data contract issues | Make build mode explicit: offline fixture mode vs live mode; avoid random fallback in production builds |
| `[popmart] No recon data found, using empty dataset` | Intentional fallback, but noisy and possibly incomplete content state | `src/_data/popmart.js` | Data loader expects `services/popmart_recon_v3_*.json` and finds none | Build succeeds with empty Popmart dataset; pages may look unfinished | Add explicit fixture/bootstrap data or gate Popmart pages when recon data is absent |
| `[test] default export invoked` | Stray debug artifact / probably should not exist | `src/_data/test.js` | A test/demo global data file is loaded on every Eleventy build and logs unconditionally | Pollutes build output and risks accidental global-data collisions | Remove or rename `src/_data/test.js`, or gate it behind a debug env flag |
| `Writing ./_site/layouts/base/index.html`, `./_site/layouts/collection/index.html`, etc. | Real structural bug | Build output and confirmed files in `_site/layouts/*` | `src/layouts/*.njk` lives under Eleventy input and is treated as renderable content, not just layouts | Produces bogus public routes for internal layout templates | Move these files out of `src/`, delete duplicates, or configure Eleventy layout directories explicitly |
| `src/layouts/*` and `src/_includes/layouts/*` both exist | Real structural duplication | Directory listing and file reads | Parallel layout trees exist, with overlapping names and divergent contents | Hard to know which layout is authoritative; encourages drift and ghost pages | Consolidate to one layout location only |
| `src/layouts/base.njk` content appears to mirror `_includes/base.njk`, while `_includes/layouts/base.njk` is different | Real drift hazard | File contents read directly | Layout copies are not only duplicated, they are semantically different | Pages may use one layout while other copies silently rot or ship as pages | Pick canonical layout tree and remove the rest |
| `src/pages/feed.njk` writes `./_site/pages/feed/index.html` instead of `feed.xml` | Real output bug | Build output + `_site/feed.xml` missing + `_site/pages/feed/index.html` exists | Front matter sets `json.permalink: "feed.xml"` instead of top-level `permalink: "feed.xml"` | RSS route is broken or missing in production | Fix front matter so feed emits actual `/feed.xml` |
| `.eleventy.js` and `eleventy.config.mjs` both exist at repo root | Real config ambiguity | Both files present and readable | Two competing Eleventy config entrypoints exist in different module systems | Very easy to edit the wrong config; uncertain which one is canonical | Collapse to a single config file and delete or archive the other |
| `src/lib/archives/index.mjs` explicitly supports both `src/content/archives` and `src/archives` | Real structural debt | Comment and code in `src/lib/archives/index.mjs` | Repo historically tolerated two archive layouts | Increases ambiguity and makes accidental duplication easier | Choose one archive source tree and remove compatibility fallback |
| `src/pages/resume/index.njk.bak` exists under source tree | Low-risk clutter / confusion source | File search | Backup artifact left inside source tree | Not currently built, but easy to misread or accidentally revive | Remove or relocate backup files outside source tree |
| `src/cannabis.njk.disabled` exists under source tree | Low-risk clutter / confusion source | File search | Disabled template left in-place | Not currently built, but adds uncertainty during audits | Remove or archive intentionally-disabled templates elsewhere |
| `vite.config.mjs` still targets `_site` with `emptyOutDir: false` while Eleventy also writes `_site` | Structural complexity / integration risk | `vite.config.mjs` | Asset pipeline and site generator both target same output directory | Easy to create collisions, stale files, or unclear ownership of output | Either fully define Vite’s responsibility or reduce Vite surface if passthrough Eleventy assets are the intended model |

---

## Priority order

### P0 — wrong output or public-route bugs

1. **Fix feed output** so `src/pages/feed.njk` writes `/feed.xml`.
2. **Stop shipping internal layouts as public pages** from `src/layouts/*`.
3. **Collapse duplicate layout trees** so there is one authoritative layout source.

### P1 — structural confusion that keeps causing bugs

4. **Choose one Eleventy config file** (`.eleventy.js` _or_ `eleventy.config.mjs`).
5. **Choose one archive source tree** (`src/content/archives` _or_ `src/archives`).
6. **Remove debug/backup/dead source artifacts** like `src/_data/test.js`, `.bak`, `.disabled` once confirmed unused.

### P2 — noisy but non-fatal runtime/data behavior

7. Replace random/localhost fallback behavior with explicit fixture/live modes for `cannabis` data.
8. Make `popmart` absence an explicit content-state decision rather than a warning surprise.

### P3 — output cleanliness and long-tail correctness

9. Investigate the malformed daisyUI/Tailwind selectors.
10. Resolve the ESM/CommonJS module warning consistently.
11. Reassess whether Vite should keep writing into `_site` directly.

---

## Concrete evidence snapshots

### Confirmed bad feed output

Observed after build:

- `_site/feed.xml` → **missing**
- `_site/pages/feed/index.html` → **present**

Source causing it:

- `src/pages/feed.njk` currently uses:

  - `json.permalink: "feed.xml"`

This looks like intent drift. Eleventy expects top-level `permalink`, not `json.permalink`, for the output route.

### Confirmed ghost layout pages

Observed after build:

- `_site/layouts/base/index.html` → present
- `_site/layouts/collection/index.html` → present
- `_site/layouts/project/index.html` → present

These should almost certainly not be public routes.

### Confirmed duplicate layout trees

Present simultaneously:

- `src/layouts/*`
- `src/_includes/layouts/*`
- `src/_includes/*.njk` layout-like files

This is not just duplicate naming — contents already differ.

---

## Suggested execution plan

### Pass 1: output correctness

- Fix `feed.njk` permalink.
- Remove `src/layouts/*` from public build input.
- Rebuild and verify unwanted `/layouts/*` routes disappear.

### Pass 2: source-of-truth cleanup

- Pick one layout tree.
- Pick one Eleventy config file.
- Pick one archives source root.

### Pass 3: noise reduction without hiding real problems

- Remove `src/_data/test.js` or gate it.
- Make `cannabis`/`popmart` data modes explicit.
- Investigate CSS optimizer warnings.
- Normalize module system.

---

## What is already fixed before this audit

These earlier issues are no longer the immediate blocker:

- Bun build no longer hangs at dependency resolution during this run.
- Eleventy passthrough collision on `theme-toggle.js` was fixed.
- Critical frontend assets now emit into `_site/assets/js` and `_site/assets/css`.
- `/about/index.html` now exists in build output.

---

## Recommendation

Do **not** treat the current successful build as "done." It is currently a **successful build with unresolved architectural weirdness**.

The biggest wins are:

1. fix feed route
2. kill ghost layout output
3. collapse duplicate layout/config/archive structures

Those three changes should make the next round of build logs dramatically easier to trust.
