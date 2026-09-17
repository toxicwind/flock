# Flock Phase 2 ABSORB — Migration Guide

**Date:** 2026-09-17  
**Scope:** Unifying AstMatrix (Go) and nim-proxy (Rust) into Flock's Rust core as the
multi-provider remote API/completions subsystem behind Herd `:25100`.

## What was absorbed

### nim-proxy → Flock core
The NVIDIA NIM proxy's serving path is now the Flock serving path:
- **Lane/FIFO/dispatcher:** 61-second sliding windows per key, 25 ms grant spacing,
  sticky lane preference, least-loaded spillover — preserved exactly.
- **Governor:** Model-pressure worker-concurrency gate — preserved exactly.
- **Circuit breaker:** 5 failures / 30 s window / 3 half-open successes — preserved.
- **Retry semantics:** Connection errors → 5 s "connect" cooldown; 429/5xx →
  upstream `Retry-After` (default 10 s); 4xx never cools the lane.
- **Timeouts:** `max_wait_secs` deadline → 504; `request_timeout` → 502 on stall.

### AstMatrix → Flock router
The Go router's machinery is now Rust in `proxy/src/router.rs`:
- **Provider registry:** 13 canonical providers (nvidia, openai, anthropic, groq,
  together, fireworks, hyperbolic, deepinfra, mistral, cohere, gemini, perplexity, xai).
- **Strategies:** Hybrid, AstRace, StickyAffinity, WeightedElo, LeastLatency,
  RoundRobin, Free, CircuitChain.
- **Health:** SQLite-backed provider/model health, imported from AstMatrix state DB.
- **Sticky affinity:** Session→provider/model with TTL, persisted.
- **Coalescer:** 5-second request coalescing for identical buffered requests.
- **Rate limiting:** Per-provider token buckets (AstMatrix's `Allow`).

## Intentional defect corrections

These AstMatrix behaviors were **bugs**, not features. They are fixed, not preserved:

| # | AstMatrix defect | Correction |
|---|------------------|------------|
| 1 | `MaxParallel` configured but race fanned out to **every** candidate | Bounded by `max_parallel`; sequential failover until racing lands |
| 2 | `FifoMax` configured but never enforced | Documented; enforcement deferred (see Limitations) |
| 3 | 5-second `RequestCoalescer` existed but was **never called** | Wired into the buffered path; leaders publish, followers share |
| 4 | Sticky lookup existed but routing never called `SetSticky` | `acquire()` sets affinity on success via `AcquireCtx.session` |
| 5 | Health maps not hydrated from SQLite on startup | `RouterHandle::build` imports AstMatrix health state |
| 6 | In-memory sticky lookup ignored persisted expiry | TTL enforced on read; stale affinities rejected |
| 7 | Race bypassed circuit/rate/health gates | `acquire()` gates every attempt: circuit → bucket → governor → FIFO |
| 8 | Hybrid accepted every status < 500, including 4xx | 4xx is terminal (no retry, no cooldown, no circuit) |
| 9 | Free accepted `err == nil` without validating HTTP status | Status always validated |
| 10 | Hybrid retried candidate order for `MaxRetries`, sleeping `(attempt+1)*500ms` | Deadline-driven; no fixed sleeps |
| 11 | Weighted selection used raw ELO; nonpositive → 1500 | Preserved (operator-visible), documented |
| 12 | Round-robin incremented before modulo | Fixed to increment-after-select |
| 13 | Circuit-chain accepted responses < 500 | Aligned with #8 |

## Behavior changes operators must know

### Model pass-through
The old proxy passed **any** model string to NVIDIA. The router filters by
`serves_model()`. The `nvidia` provider keeps `models: ["*"]` (wildcard) after
v1 migration and fresh setup, preserving pass-through. Other providers only
serve their listed models. A request for a model no provider lists → **502**
(no provider serves model), not a fan-out.

### Buffered vs streaming
- **Buffered** (`stream: false`): Fully multi-provider. Router selects, acquires,
  fails over across providers.
- **Streaming** (`stream: true`): **NVIDIA-only** in this phase. The 285-line
  SSE retry loop (heartbeat, fallback injection, stall detection) was not
  generalized. Multi-provider streaming is deferred work.

### Failover, not racing
The buffered path uses **sequential failover**: try candidate 1, on retryable
failure try candidate 2, etc. Bounded racing (`max_parallel` concurrent attempts,
first success wins, losers cancelled) is deferred. `max_parallel` is read but
not yet enforced as a concurrency bound.

### Retry-After is honored
A 429 with `Retry-After: 1` cools the lane for 1 second, not the old fixed
backoff. The default when the header is absent is 10 s.

### Coalescing is on by default
Identical buffered requests within 5 s share one upstream call. The leader's
body-read failure surfaces as **502**, never an empty 200.

### Setup seeds NVIDIA pass-through
Fresh `/setup` configures `nvidia` with `models: ["*"]`, matching the v1
migration. The canonical 13-provider defaults (with specific model lists) apply
to the registry; the legacy single-upstream keeps its pass-through.

## Configuration

### New: providers registry
`StoredConfig.providers`: the 13 canonical providers. Each has:
- `name`, `display_name`, `base_url`, `enabled`
- `keys[]`: `{key, key_env, owner, enabled, rpm}`
- `models[]`: served model IDs, or `["*"]` for pass-through
- `model_map{}`: alias → upstream ID rewriting
- `default_rpm`, `free_tier`, `elo`

### New: routing config
`StoredConfig.routing`:
- `strategy`: hybrid (default), astraces, sticky, elo, latency, roundrobin, free, circuit
- `max_retries`: failover rounds for multi-candidate (default 3)
- `max_parallel`: race width (read; enforcement deferred)
- `fifo_max`: dispatcher queue cap (read; enforcement deferred)
- `enable_coalescing`: default true
- `sticky_ttl_secs`: affinity TTL

### Unchanged
`upstream.base_url`, `upstream.nim_keys`, `limits.*`, `client_auth`, `governor` —
all preserved. The providers registry is the source of truth; `upstream` is a
downgrade mirror synced on every save.

## Health import
On first boot with no state DB, Flock imports from AstMatrix's SQLite:
- `provider_health` (failures nullable → treated as unknown, not zero)
- `model_health` (latest window per provider/model)
- `model_state` (persistent)
- `elo` (optional; nonpositive → 1500 per AstMatrix rule)
- `session_affinity` (fresh accepted; stale rejected)
- Raw `ast_*` tables archived, never mutated.

Credentials are **never** copied. The import reads health tables only.

## Metrics
New:
- `flock_route_errors_total{provider,status}`
- `flock_lane_cooldown_total{lane,status}` — now emitted by the router
  (previously only the proxy's serving path)

Preserved: `flock_requests_total`, `flock_lane_requests_total`,
`flock_queue_wait_seconds`, `flock_active_requests`, `flock_worker_exhausted_total`,
`flock_model_limit`, `flock_affinity_total`, `flock_completion_tokens_total`.

## Limitations (honest)
1. **Streaming is NVIDIA-only.** Multi-provider SSE is deferred.
2. **No bounded racing.** Sequential failover only; `max_parallel` not enforced.
3. **`fifo_max` not enforced.** The dispatcher queue is unbounded.
4. **Model discovery** (`/v1/models` per-provider refresh) is cached/static.
5. **ELO** uses AstMatrix's raw rule (nonpositive → 1500); no decay.

## Rollback
This is an additive redesign. The live `:8000` binary, `/home/toxic/.flock/flock`,
and `/home/toxic/.flock-data` were **not touched** by Phase 2. The release is
staged at `/home/toxic/.flock/flock.next-20260917`; it does not replace the live
binary until Chris explicitly orders the cutover.
