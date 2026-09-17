# Flock Audit — 2026-09-17

## 1. Operational Summary & Telemetry

**Scope:** Maximal audit of Flock (Rust NVIDIA NIM proxy/router) plus
implementation of killer features ported from the TypeScript sovereign-router
reference: substance guard, empty-completion failover, and empty-strike
tracking.

**Baseline (2026-09-17 ~15:33 MDT):**

- Local and remote `main` HEAD: `e79737a439b64d7df1c00062331aaf54b87849e0`
- Live binary timestamp: 2026-09-17 14:38 MDT
- Worktree: `/home/toxic/flock-audit-20260917`, branch `audit/20260917`

**Completion (2026-09-17 ~17:20 MDT):**

- Merged to `main`: `34effe31` (merge of `f182b4b3`)
- Pushed to `origin/main`: verified `34effe31`
- Test suite: **385 passed, 0 failed** (256 unit + 121 e2e + 8 doc)
- Live binary redeployed: `/home/toxic/.flock/flock` (PID 2094338, :8000)

**Live routing verification (2026-09-17):**

- Authenticated `/v1/models`: 103 models, including current NVIDIA IDs
  (`nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-super-120b-a12b`,
  `nvidia/nemotron-3-ultra-550b-a55b`, `moonshotai/kimi-k2.6`, `z-ai/glm-5.3`)
- Ten-probe run: 10/10 HTTP 200 non-empty (latencies 0.331s–28.836s)
- Empty-completion defect reproduced: `z-ai/glm-5.3` returned HTTP 200 in
  18.27s with `message.content = null` — direct evidence that HTTP 200 alone
  cannot count as route success.

## 2. Root-Cause Architectural Mechanics

### Empty completions served as blank 200s

`proxy::buffered()` called `RouterHandle::execute_buffered()`, which treated any
2xx as success and relayed bytes verbatim. A model returning
`{"choices":[{"message":{},"finish_reason":"stop"}]}` produced a blank HTTP 200
to the client — indistinguishable from success at the HTTP layer. Root cause:
success was defined by HTTP status, not payload substance. This mirrors the
sovereign-router `routeAstRace` hole closed in commit `b32fc60690`
(gather-then-pick set `best` = first ok result in candidate order even with
empty content).

### Stale model IDs vs router failure

Earlier 404/410 failures were stale/inaccessible model IDs
(`nvidia/llama-3.1-nemotron-70b`, `meta/llama-3.1-8b-instruct`, etc.), not router
defects. The 410 bodies explicitly reported model end-of-life. Current model
IDs route correctly; ID rot is a catalog problem, not a routing problem.

### Buffered vs streaming asymmetry

Multiprovider routing (`RouterHandle::execute_buffered`) is active for buffered
requests. Streaming remains on the legacy NVIDIA-only path (direct
`state.dispatch`, `cfg.base_url`, old `upstream_request()`). No full-path
parity yet — documented as remaining work (section 7).

### Hung-body 200 (test regression root cause)

`Behavior::Hang` mock sends one SSE chunk then stalls mid-body. Under the new
guards the stalled partial response entered the candidate set, and the retry
path popped the mock's default response — masking the hang as a second
candidate. Fix: hang detection distinguishes a stalled stream from a completed
empty body, and the retry path no longer pops the mock default (test-harness
fix; production retry semantics unchanged).

### Empty-retry exhaustion semantics

When every candidate in the pool returns an empty completion, further retry is
futile: `empty_count >= candidates.len()` short-circuits to an honest 502
(`empty_completion`) instead of looping. Fail-fast, never fail-silent.

## 3. Primary-Source Evidence & Dataframe State

- Authenticated `GET /v1/models` on :8000 returned **103 models** under the live
  NVIDIA key pool. Current IDs verified present:
  `nvidia/nemotron-3.5-lightning-30b-a3b`,
  `nvidia/nemotron-3-super-120b-a12b`,
  `nvidia/nemotron-3-ultra-550b-a55b`,
  `moonshotai/kimi-k2.6`, `z-ai/glm-5.3`.
- Ten-probe run against the live binary: **10/10 HTTP 200, all non-empty**,
  latencies 0.331s–28.836s.
- Defect reproduction (pre-patch binary): `z-ai/glm-5.3` probe — HTTP 200,
  18.27s, `message.content = null`. Byte-level evidence the old path served
  this as success.
- Stale-ID evidence: `nvidia/llama-3.1-nemotron-70b` → 404/410 with an
  end-of-life body; classified as ID rot, not a routing defect.
- Test evidence: **385 passed, 0 failed** — 256 unit + 121 e2e + 8 doc. E2E
  coverage includes the empty-completion failover path and strike-decay timing.
- Metric surface: `flock_model_empty_strikes` gauge per model, observed in
  /metrics output during probe runs; strikes decay on a 10-minute window.

## 4. Live Patch & Code Mutation Manifest

Commit `f182b4b3` ("flock: empty-completion substance guard with failover and
strike tracking"), merged as `34effe31` (`audit/20260917` → `main`), pushed to
`origin/main`:

- `observation::has_substance()` — new predicate: a completion has substance
  iff at least one choice carries non-empty `message.content` (or
  `tool_calls`). Every routing layer consults it; HTTP 200 with no substance
  is a failure.
- Empty-completion failover — `execute_buffered` retries the next candidate on
  an empty completion instead of serving the blank; full-pool exhaustion
  (`empty_count >= candidates.len()`) → honest 502 `empty_completion`.
- Empty strikes — per-model strike counter with 10-minute decay, exposed as the
  `flock_model_empty_strikes` metric. A strike is recorded on each empty
  completion; decayed strikes fall off the gauge automatically.
- `ExecuteOutcome::Buffered` — new outcome variant distinguishing a buffered
  completion from streamed/other outcomes in the router's result type.
- `ProviderMeta` — provider metadata struct (name, base URL, key-pool
  identity) threaded through the router for per-provider attribution.
- `aggregate_models()` enrichment — `/v1/models` now aggregates across
  providers with enriched metadata (provider, source) instead of raw
  passthrough.
- Test fixes — hung-body 200: retry no longer pops the mock default on a
  stalled SSE body; empty-retry exhaustion test asserts the 502 boundary.
- Six e2e regressions in the buffered execution path fixed en route
  (`9d4d685f`).

No reverts. Additive only.

## 5. Idempotency & Blast-Radius Verification

- The patch is purely additive: one new predicate, one new outcome variant,
  one new metric, one new retry branch. No existing function signature changed
  in a breaking way; no behavior removed.
- `finish_failure(200)` semantics preserved and safe: failure recording carries
  no cooldown and trips no circuit breaker — a 200-with-empty-content now
  records as a failure without penalizing the provider's circuit state.
- Idempotency: re-running the merge produces no diff (merge commit `34effe31`
  is the single integration point); strike counters are keyed per model and
  decay idempotently; `aggregate_models()` is a pure aggregation over the
  provider registries.
- Blast radius: confined to the buffered execution path and the `/v1/models`
  aggregation. The streaming path is untouched (still legacy NVIDIA-only).
- Live binary redeploy (`/home/toxic/.flock/flock`, PID 2094338, :8000)
  verified healthy post-deploy: /health 200, 10/10 probes green, metrics
  flowing.
- No daemons restarted beyond the flock binary itself; no config-file
  mutation; no credential touched.

## 6. Ecosystem Cross-References & Downstream Sync

- **sovereign-router-ts (live, :25104)** — the reference implementation this
  ports from. The substance guard closed the identical hole there (commit
  `b32fc60690`); the flap tracker with empty strikes is already live at
  /metrics (`sovereign_router_model_empty_strikes`). Flock's
  `flock_model_empty_strikes` mirrors that metric name family for cross-stack
  correlation.
- **Herd / llama-swap (:25100)** — two defects observed during the audit, both
  out of scope for this patch but recorded here:
  - `GET /v1/v1/models` → 404: doubled path prefix in the herd client/config;
    the correct path is `/v1/models`.
  - pitchfork reports herd "errored"/stopped while PID 2022955 is healthy and
    serving 200 on :25100 — stale supervisor ownership. Do NOT kill the
    healthy daemon or start a duplicate.
- **Flock rename (nim-proxy → flock)** — tree already renamed (commits through
  `e09a4890`, "flock: full nim-proxy rename + key-pool absorption + e2e
  green"); no remaining astmatrix references in the live tree.
- **Dagger build lane** — unaffected; buildsrv remains fallback-only.

## 7. Next Autonomous Trajectory

Remaining work, in priority order:

1. **Streaming parity** — port the substance guard + failover to the streaming
   path (the `handleStream` equivalent); streaming currently stays on the
   legacy NVIDIA-only route.
2. **Strike-driven routing** — consume `flock_model_empty_strikes` in
   candidate ordering (bench models with strikes, as sovereign-router does
   after 3 empties in 10 min).
3. **Persistent strikes** — strikes currently live in memory; persist across
   restarts (sled/sqlite or metrics-backed restore).
4. **Six remaining providers** — together, fireworks, hyperbolic, github,
   openai, perplexity, siliconflow (per the sovereign-router consolidation
   plan).
5. **Herd path fix** — correct the doubled `/v1/v1/models` path; resolve
   pitchfork's stale ownership of PID 2022955 without disturbing the healthy
   daemon.
6. **Router strategy gaps** — coalescing, least-latency, and round-robin in
   Flock's router, matching sovereign-router's remaining gaps.

---

*Audit run 2026-09-17 ~15:33–17:20 MDT. Branch `audit/20260917` merged as
`34effe31`, pushed to `origin/main`. 385/385 tests green. Live:
`/home/toxic/.flock/flock` (PID 2094338) on :8000.*
