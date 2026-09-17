# NIM → Flock feature-parity matrix

2026-09-17. Every stray NVIDIA-NIM implementation found on awrawr-pc and
GitHub, and where its behavior now lives in the merged Flock tree
(`toxicwind/flock`). Zero feature loss; zero standalone `nim-proxy`
product naming remains.

| # | Stray implementation | Unique behavior | Absorbed into Flock as |
|---|---|---|---|
| 1 | `nim-proxy-final.sh` (Docker installer + setup wizard: 40 RPM/key, `npk_` client keys, OpenCode/Nanocoder/Tau wiring, health + smoke checks) | installer UX, daemon install, key minting, client wiring | `flock-final.sh` (repo root) — same behaviors, Flock naming, no destructive cleanup |
| 2 | Rust binary v0.6.5 (`/home/toxic/.nim-proxy/nim-proxy`, `/home/toxic/.docker-offload/nim-root/nim-proxy`) | the proxy itself | `proxy/` source v0.6.6 — superset; binaries retired, one canonical build |
| 3 | super-ralph `src/nimProxy.ts` — `NimProxyKeyPool` (multi-key round-robin, 429 parks key honoring `Retry-After`, opaque `key#N` stats), `parseRetryAfterMs`, `proxyChatCompletions` per-key rotation | client-side key rotation on 429 | `client/src/keypool.ts` (`FlockKeyPool`, `splitKeys`, `parseRetryAfterMs`) wired into `FlockClient.request()`; Python mirror `client/python/flock_client/keypool.py`. Proxy-side, the Rust governor already honors `Retry-After` per lane (`proxy.rs::backoff_for`) |
| 4 | `nimprobe.py` (60-line urllib probe: 13 models × chat/validate) | quick model probe driver | covered by `client/` examples + `FlockClient.probeModel()` |
| 5 | `nim-rewire.py` (one-shot patcher for old paths) | nothing reusable — targeted pre-merge paths | obsolete; no absorption needed |
| 6 | `gk-live-gear/nvidia-nim-loader/` (`nim.py` probes, `nim_proxy.py` ephemeral-port auth-injecting forwarder) | ephemeral-port forwarder pattern, probe/benchmark scripts | forwarder pattern covered by the proxy itself; probe scripts covered by `tools/` + `benchmarks/` |
| 7 | swarm-merge `work/nim/client.py` (fail-fast no-retry semantics, cold-start/dead-model guards, probe-before-use) | dead-model guard, fail-fast option | `FlockClient.listModels()` + `probeModel()` (TS + Python); fail-fast = `maxRetries: 0` |

Deliberately NOT renamed (compatibility, not product naming):
- `nimproxy-history` record format marker (on-disk history DB compatibility)
- `X-Nim-Keys-Deadline` header and `/api/settings/nim-keys` route (client-facing API surface)
- `NIM API key` user-facing labels (NVIDIA's product name for the credential)
- Upstream provenance: proxy core derives from `miztertea/nim-proxy` (MIT)

Remote-only, no local clone (evidence, untouched):
- `toxicwind/nvidia-nim` (fork; `models/catalog.parquet` on main)
- `toxicwind/nim-audit`, `toxicwind/nim-proxy-audit-20260915`,
  `toxicwind/nvidia-nim-model-probe`, `toxicwind/nvidia-swarm-lens`
- `evmts/super-ralph` — read-only evidence; never pushed (standing rule)
