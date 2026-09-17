---
name: docx
description: "Create and edit Word documents (.docx) — C# + OpenXML SDK for creation, WIR engine for editing/comments/tracked changes. Use for any .docx task including document creation, editing, comments, revisions, footnotes, TOC, and Markdown-to-Word conversion."
---

# Part 1: Routing

`read file` / `cat` only extracts plain text from `.docx` — all formatting is lost. If the task involves appearance or structure, use WIR engine's `session.read()` instead.

## Route = What You Have

**1. WIR** (`references/wir-reference.md`) — A .docx exists whose **format/style matters** to the output.

The user provides a template, a document to edit/modify/review/annotate, or any file whose formatting should be preserved or referenced. This file is your output foundation — read it, modify it, fill it.

For existing `.docx` edits or redesigns, WIR is the required first path; use Create only when the file is merely a data source or after a named WIR failure.

If the .docx is merely a content/data source (e.g., reference papers, raw data exports) and its formatting is irrelevant, just `read file` to extract text — that is NOT a WIR case.

`.doc` format → convert first: `libreoffice --headless --convert-to docx`

**2. md2docx** (`references/md2docx-reference.md`) — A Markdown file is the intended content source for a new Word document.

Use md2docx when ANY of these conditions applies:

- You are the Orchestrator/Swarm and are producing a new `.docx`; assemble the complete Markdown first, then convert it with md2docx.
- The user explicitly requests Markdown-to-Word conversion or asks to use md2docx.
- Another skill, including Deep Research, requires a Markdown-first handoff to DOCX.
- An upstream agent or workflow has already returned the `.md` that should become the document body.

When a complete `final.md` and its `citation.jsonl` are supplied, treat them as the finished content and citation inputs: do not restart research or rewrite the report, and use the supplied citation file for conversion.

These triggers do not override WIR for editing an existing `.docx` whose formatting must be preserved. If there is no existing DOCX and no Markdown-first trigger, use Create.

**3. Create** (`references/openxml-sdk-reference.md`) — Neither of the above.

No target .docx, no upstream .md. Build the document from scratch using C# + OpenXML SDK via `./scripts/docx build`.

---

# Part 2: Execution

## File Structure

```
docx/
├── SKILL.md                       ← This file (routing + rules)
├── references/
│   ├── openxml-sdk-reference.md   → Creation: patterns, traps, all you need
│   ├── wir-reference.md           → WIR editing interface + patterns
│   ├── md2docx-reference.md       → Citation pipeline → Word conversion
│   ├── chart-reference.md         → Native Word charts (pie, bar, line)
│   ├── omml-reference.md          → OMML math equation patterns
│   └── matplotlib-guide.md        → Charts Word can't do natively
├── scripts/
│   ├── docx                       → Unified entry point for Create/validate
│   ├── engine/                    → WIR engine (editing core)
│   ├── md2docx/                   → Citation → Word pipeline
│   ├── generate_backgrounds.py    → Style reference: Morandi curves (read for technique, don't call directly)
│   ├── generate_inkwash_backgrounds.py  → Style reference: ink wash
│   ├── generate_swiss_backgrounds.py    → Style reference: Swiss grid
│   ├── generate_geometric_backgrounds.py → Style reference: geometric blocks
│   ├── generate_gradient_backgrounds.py  → Style reference: gradient ribbons
│   └── generate_formal_backgrounds.py    → Style reference: formal double border
└── assets/templates/
    ├── Example.cs                 → English document demo (conditional required)
    └── CJKExample.cs              → Chinese/CJK document demo (conditional required)
```

## Validation

- **Creation**: `./scripts/docx build` runs the full pipeline (compile → generate → auto-fix element order → OpenXML validate → business rules)
- **Editing**: The engine validates internally; after saving, spot-check high-risk areas; for layout-sensitive edits, convert to PDF/images when available to visually confirm the result
- **md2docx**: Use the converter's own feedback, verify that the resulting package opens cleanly, and render it for visual review. `./scripts/docx validate` belongs to the C# Create route and is not the md2docx validator.

## Hard Rules

1. WIR first for editing — no ad-hoc XML surgery; no `python-docx` unless a specific WIR operation has failed and you can name the failure. Consult `references/wir-reference.md` before falling back.
2. Process large documents in windows — no oversized replacement blocks.
3. On warnings or errors, stop, re-read, then continue.
4. Treat md2docx warnings and errors as actionable feedback: preserve their full context, resolve the reported problem in a working copy, and retry until the requested DOCX passes validation. Never suppress a conversion f