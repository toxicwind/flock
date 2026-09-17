# ASTMATRIX V2 — APPLY & PUSH INSTRUCTIONS

## Download

Download the clean tar.gz:
```bash
curl -L -o astmatrix-v2-clean.tar.gz   "https://agents-file-output.sandbox/astmatrix-v2-clean.tar.gz"
```

Or use the file at: /mnt/agents/output/astmatrix-v2-clean.tar.gz

## Apply to Your Fork

```bash
# 1. Download and extract
cd ~/projects/llama-swap-main  # or wherever your fork is
tar -xzf /path/to/astmatrix-v2-clean.tar.gz

# 2. Copy astmatrix module
mkdir -p internal/astmatrix
cp internal/astmatrix/*.go internal/astmatrix/

# 3. Apply config patch (adds AstMatrixConfig to Config struct)
patch -p1 < patches/config.go.patch || cp patches/config.go.new internal/config/config.go

# 4. Apply server patch (adds cloud dispatch logic)
patch -p1 < patches/server.go.patch || cp patches/server.go.new internal/server/server.go

# 5. Add sqlite3 dependency
go get github.com/mattn/go-sqlite3

# 6. Build and verify
go build ./...
go test ./internal/astmatrix/...

# 7. Configure (add to your config.yaml)
cat >> config.yaml << 'YAML'
astMatrix:
  enabled: true
  strategy: hybrid
  astStrategy: ast_race
  requestTimeout: 95
  maxRetries: 3
  healthProbeInterval: 30
  enableCoalescing: true
  providers:
    openrouter:
      baseUrl: https://openrouter.ai/api/v1
      keyEnv: OPENROUTER_API_KEY
      models: [openrouter/auto]
    groq:
      baseUrl: https://api.groq.com/openai/v1
      keyEnv: GROQ_API_KEY
      freeTier: true
      models: [groq/llama-3.1-70b-versatile]
YAML

# 8. Commit
git add internal/astmatrix internal/config/config.go internal/server/server.go go.mod go.sum
git commit -m "feat: astmatrix v2 production-grade cloud router

- 8 routing strategies: hybrid, ast_race, sticky_affinity, weighted_elo,
  least_latency, round_robin, free, circuit_chain
- Circuit breakers with half-open probe recovery
- Health probes: background 5s checks every 30s
- Request coalescing: deduplicates identical concurrent requests
- Streaming SSE: proper flush every 32KB
- Retry with exponential backoff: 3 attempts per provider
- Rate limiting: token bucket per provider
- Latency tracking: exponential moving average per provider
- Sticky sessions: session affinity via Authorization header
- Model mapping: local model IDs to provider-specific IDs
- 13 built-in providers: openrouter, nvidia, groq, together, cerebras,
  fireworks, hyperbolic, github, mistral, openai, perplexity, siliconflow
- Status endpoint: /astmatrix/status and /astmatrix/metrics"

# 9. Push to your fork
git push origin main

# 10. (Optional) Push to upstream as PR
git remote add upstream https://github.com/mostlygeek/llama-swap.git
git push upstream HEAD:refs/heads/astmatrix-v2-prod-router
```

## Files Delivered

| File | Lines | Purpose |
|------|-------|---------|
| config.go | 62 | YAML config structs with production defaults |
| circuit.go | 97 | Circuit breaker: Closed→Open→Half-Open→Closed |
| coalescer.go | 64 | Request deduplication cache |
| metrics.go | 81 | Latency histograms, error rates, throughput |
| providers.go | 177 | 13 built-in providers with model lists |
| healthdb.go | 114 | SQLite health DB + EMA latency + sticky sessions |
| ratelimit.go | 56 | Token bucket per provider (60/min paid, 10/min free) |
| router.go | 450 | Main HTTP handler with 8 strategies |
| matrix.go | 33 | Coordinator wrapper (compatibility) |
| ui.go | 68 | /astmatrix/status and /astmatrix/metrics endpoints |

## Production Checklist

- [ ] `OPENROUTER_API_KEY` or other provider keys set in env
- [ ] `astMatrix.enabled: true` in config.yaml
- [ ] `go build ./...` passes
- [ ] `go test ./internal/astmatrix/...` passes
- [ ] Health probes show providers healthy at `/astmatrix/status`
- [ ] Streaming responses work via SSE with proper flush
- [ ] Circuit breakers recover after failures
- [ ] Rate limiting prevents provider bans
- [ ] Request coalescing reduces duplicate load
