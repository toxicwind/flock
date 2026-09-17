# Layout Modularization Contract (2026-03-12)

This document defines the canonical layout architecture after the merge-first refactor.

## Goals

- Maximize shared layout behavior while preserving page-specific UX.
- Keep `consulting` and `resume` fully standalone (subdomain-safe) and uncoupled from main nav/chrome.
- Preserve compatibility with legacy `layout:` frontmatter values via shim wrappers.
- Prevent ghost route generation from source layout files.

## Canonical Layout Namespaces

- `src/_includes/layouts/main/*`
  - Main site shell/layouts (`base`, `collection`, `project`).
- `src/_includes/layouts/subdomains/consulting/*`
  - Standalone consulting shell + page composition.
- `src/_includes/layouts/subdomains/resume/*`
  - Standalone resume shell + page composition.
- `src/_includes/layouts/utility/*`
  - Utility layouts (`embed`, `redirect`).

## Compatibility Shim Policy

The following remain valid for legacy content and should map to canonical targets:

- `base.njk` -> `layouts/main/base.njk`
- `collection.njk` -> `layouts/main/collection.njk`
- `project.njk` -> `layouts/main/project.njk`
- `consulting.njk` -> `layouts/subdomains/consulting/page.njk`
- `resume.njk` -> `layouts/subdomains/resume/page.njk`
- `embed.njk` -> `layouts/utility/embed.njk`
- `redirect.njk` -> `layouts/utility/redirect.njk`

This applies both in:

- `src/_includes/*.njk`
- `src/_includes/layouts/*.njk`

## Standalone Isolation Rules

For `consulting` and `resume` pages:

- Must not render main-site header/nav/footer chrome.
- Must not rely on `components/header.njk` or main navigation data structures.
- Must provide complete HTML document shells in their subdomain layout namespace.

## Build/Config Guardrails

- `eleventyConfig.ignores.add('src/layouts/**')` in both `.eleventy.js` and `eleventy.config.mjs`.
- Interlinker/plugin default layout set to `layouts/utility/embed.njk`.

## Verification Snapshot

Validated on Linux using Bun + Eleventy build:

- Clean build succeeds.
- No generated `_site/layouts/*` ghost routes.
- `_site/consulting/index.html` and `_site/resume/index.html` do not include main-site nav/header markers.
