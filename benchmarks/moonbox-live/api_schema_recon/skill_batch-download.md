---
name: batch-download
type: capability
description: >
  Multi-agent batch download and data collection orchestration. Use this skill whenever
  the task requires discovering, validating, and downloading multiple files or datasets
  from the web — batch report downloads, multi-source data collection, structured web
  scraping, file archival, or any task demanding parallel discovery and retrieval with
  verification. This skill enforces plan-first decomposition, parallel sub-agent delegation,
  evidence-based URL discovery, strict output validation, and structured result integration.
  Do NOT use for: single file download, simple API calls, tasks that don't involve
  web discovery or file retrieval.
---

# Batch Download

Orchestrate multi-agent batch discovery and retrieval: plan the task decomposition, delegate atomic subtasks to parallel sub-agents, gather and verify evidence, then integrate and validate all results into a structured deliverable. The Orchestrator coordinates — sub-agents execute.

## Workflow Decision Tree

Determine the entry point based on user input:

```
User Query
  │
  ├─ Type A — Targets unknown (must search first)
  │   → Phase 1 (Plan) → Phase 2 (Search & Discovery)
  │     → Phase 3 (Parallel Download) → Phase 4 (Integrate & Validate)
  │
  ├─ Type B — Targets already provided (URLs / file list given)
  │   → Phase 1 (Plan) → Phase 2 (URL Validation & Pattern Discovery)
  │     → Phase 3 (Parallel Download) → Phase 4 (Integrate & Validate)
  │
  └─ Hybrid — Some targets known, some must be discovered
      → Phase 1 (Plan) → Phase 2 (Partial Search + Validation)
        → Phase 3 (Parallel Download) → Phase 4 (Integrate & Validate)
```

All types follow the same 1→2→3→4 sequence. The difference is Phase 2's scope: Type A performs full search, Type B validates known URLs and discovers patterns, Hybrid does both.

## Phase 1: Task Decomposition (Orchestrator Only)

**Goal**: Break the user request into clear, atomic, verifiable subtasks before any execution.

**Process**:
1. Restate the user's request in operational terms
2. Identify the task type (Type A / Type B / Hybrid) based on whether target URLs are known
3. Decompose into atomic subtasks:
   - Each subtask has **one well-defined goal** (e.g., "download report for 2021 from URL X")
   - Each subtask is **independent** where possible (to enable parallelization)
   - Each subtask has **explicit success criteria** (file type, size, content validation)
4. For multi-dimensional requests (different years / regions / categories / file types / data sources), create **one subtask per dimension**
5. Plan search subtasks explicitly (if Type A or Hybrid):
   - Do NOT assign "all search" to a single agent when multiple independent searches are possible
   - **Parallelize partitionable search spaces**: by year, by site, by category, by alphabet range, by region — each partition gets its own search sub-agent
   - Plan **retry strategies**: if a search attempt fails, plan alternative queries, sites, or filters as new subtasks rather than giving up
6. If the search task is complex, split into multiple sequential stages (e.g., find index page → extract file links → validate → download)

No execution in this phase — planning only.

## Phase 2: Evidence Gathering & Pattern Discovery

**Goal**: Discover target URLs, validate them, and identify download patterns before batch execution. **All task types execute this phase** — the scope varies by type.

### Pattern Discovery (Critical)

Before delegating downloads, actively look for **URL patterns and structural regularities** in the download targets:
- **Numeric patterns**: URLs with incrementing page/year/ID numbers (e.g., `report_2020.pdf`, `report_2021.pdf`, ... or `page=1`, `page=2`, ...)
- **Directory patterns**: files organized in predictable folder structures (e.g., `/data/2023/Q1/`, `/data/2023/Q2/`)
- **Naming conventions**: consistent filename templates across a site (e.g., `{company}_annual_{year}.pdf`)
- **Pagination patterns**: API or page parameters that follow arithmetic sequences (e.g., `offset=0,10,20,...`)
- **Site structure**: index pages, sitemap.xml, or listing pages that enumerate all downloadable resources

When a pattern is discovered:
1. **Verify** the pattern holds by testing 2–3 instances
2. **Extrapolate** all target URLs from the pattern
3. Use Python scripts to **programmatically generate** the full URL list when the pattern is clear
4. Fall back to individual search only for URLs that break the pattern

### URL Handling Rules

1. **Never fabricate URLs** — only use:
   - URLs explicitly provided by the user
   - URLs discovered via web search or browser visit
   - URLs extrapolated from **verified patterns** (e.g., page1→page2→...→pageN after confirming the pattern holds)
   - URLs extracted by Python-based fetching + HTML parsing

2. **Prefer Python-based parsing when browser tools are inefficient**:
   - Use `python + requests/httpx` to fetch HTML
   - Use `Beau