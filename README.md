# flock

Herd's cloud-API completions scaffold — the maximal NVIDIA NIM plugin. Named for the
flock: the herd's sky counterpart. Not local models — APIs.

One merged tree (2026-09-17), renamed in full from the eight scattered NIM projects.
Previously `nim-proxy` (+ clients, tools, dashboards, benchmarks); now one thing.

| Path | What it is | Origin |
|---|---|---|
| `proxy/` | **flock** — Rust rate-limit proxy for NVIDIA NIM (`integrate.api.nvidia.com`), OpenAI-compatible, dashboard + history store. Live daemon on `:8000`. | nim-proxy |
| `client/` | NIM API clients (TypeScript + Python) | nim-client |
| `dashboard/` | Benchmark dashboard (Bun) | nim-bench-dashboard |
| `tools/` | CLI toolkit (`nvt.py`) + free-endpoint inference script | nvidia-nim-tools, nvidia-free-endpoints |
| `research/` | Inkling API research (Go) | nim-inkling-api-research |
| `benchmarks/moonbox-20260822/` | Moonbox NIM benchmark snapshot | moonbox-nim-benchmark-2-20260822 |
| `benchmarks/moonbox-live/` | Live benchmark runs + captures | moonbox-live |

## Wiring

- The sovereign router's `nvidia` provider and herd's AstMatrix both terminate at
  flock's `:8000` — flock is the local enforcement point and owns the
  canonical provider definitions (nim-proxy absorbed 2026-09-17).
- Upstream provenance: the proxy core derives from
  [miztertea/nim-proxy](https://github.com/miztertea/nim-proxy) (MIT).

## Herd docs

`projects/herd/docs/flock/` — overview, architecture, herd integration, runbook.
