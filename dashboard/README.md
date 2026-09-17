# NIM Bench Dashboard — All Forks Consolidated

Pretty HTML dashboard for NVIDIA NIM community history.db benchmarks.

## What this is
- Auto-found via gh cli: 28 repos, 57 raw files from raw.githubusercontent.com
- All forks of ahmedhabibo/NIMStats template (90% forks)
- Consolidates history.db / history.db.gz with exact terms like "deepseek-v4-pro-0813", "minimax-m3", "nemotron-3-ultra-550b"

## Structure
```
/home/toxic/projects/nim-bench-dashboard/
  package.json — bun + chart.js + hono
  src/server.ts — bun server on :3000
  public/index.html — pretty dashboard
  scripts/save_all.py — copies /tmp/nim-bench-*/dbs/* -> data/ + builds consolidated.json
  data/ — history.db files + consolidated.json + manifest.json
```

## Extract & Run (on your machine toxic@awrawr-pc)
```bash
# 1. extract
tar -xzf nim-bench-dashboard.tar.gz -C /home/toxic/projects/
cd /home/toxic/projects/nim-bench-dashboard

# 2. save all dbs from previous gh crawl
python3 scripts/save_all.py
# copies /tmp/nim-bench-*/dbs/*__history.db* -> ./data/

# 3. install bun deps (no reinventing wheel)
bun install

# 4. launch pretty html
bun run dev
# or
bun src/server.ts

# Opens http://localhost:3000
# auto hot reload
```

## If you want to re-crawl forks again:
```bash
chmod +x ../Nim-Auto-Find-Gh.sh
./Nim-Auto-Find-Gh.sh
# then
python3 scripts/save_all.py
bun run dev
```

## Features
- Stats cards: repos, DBs, total runs, total results
- Bar chart: runs vs results per fork
- Horizontal bar: fastest models overall avg response_time
- Searchable table of all forks with top model
- Raw exact_terms_found from strings history.db

Enjoy — no self-benchmark needed.
