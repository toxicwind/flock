![llama-swap header image](docs/assets/hero4.webp)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mostlygeek/llama-swap/total)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/mostlygeek/llama-swap/go-ci.yml)
![GitHub Repo stars](https://img.shields.io/github/stars/mostlygeek/llama-swap)

# llama-swap


> **→ Fork:** [toxicwind/llama-swap](https://github.com/toxicwind/llama-swap) — based on [mostlygeek/llama-swap](https://github.com/mostlygeek/llama-swap).  
> *Last synced with upstream: **Jul 20, 2026** — [diff](https://github.com/toxicwind/llama-swap/compare/main...mostlygeek:llama-swap:main)*

Upstream docs are below. **Fork-only changes are first** so they are obvious.

Run multiple generative AI models on your machine and hot-swap between them on demand. llama-swap works with any OpenAI and Anthropic API compatible server and is used by thousands of people to power their local AI workflows.

---

## 🔱 toxicwind/llama-swap

- ✅ Easy to deploy and configure: one binary, one configuration file. no external dependencies
- ✅ On-demand model switching
- ✅ Use any local OpenAI compatible server (llama.cpp, vllm, tabbyAPI, stable-diffusion.cpp, etc.)
  - future proof, upgrade your inference servers at any time.
- ✅ OpenAI API supported endpoints:
  - `v1/completions`
  - `v1/chat/completions`
  - `v1/responses`
  - `v1/embeddings`
  - `v1/models` - list available models
  - `v1/audio/speech` ([#36](https://github.com/mostlygeek/llama-swap/issues/36))
  - `v1/audio/transcriptions` ([docs](https://github.com/mostlygeek/llama-swap/issues/41#issuecomment-2722637867))
  - `v1/audio/voices`
  - `v1/images/generations`
  - `v1/images/edits`
- ✅ Anthropic API supported endpoints:
  - `v1/messages`
  - `v1/messages/count_tokens`
- ✅ llama-server (llama.cpp) supported endpoints
  - `v1/rerank`, `v1/reranking`, `/rerank`
  - `/infill` - for code infilling
  - `/completion` - for completion endpoint
  - `/props` - requires `?model={model_id}` query parameter to be provided. The autoload parameter is not supported and will be ignored.
- ✅ SDAPI via [stable-diffusion.cpp's server](https://github.com/leejet/stable-diffusion.cpp/tree/master/examples/server)
  - `/sdapi/v1/txt2img`
  - `/sdapi/v1/img2img`
  - `/sdapi/v1/loras` - requires `model` in request body to fetch the correct loras
- ✅ llama-swap API
  - `/ui` - web UI
  - `/upstream/:model_id` - direct access to upstream server ([demo](https://github.com/mostlygeek/llama-swap/pull/31))
  - `/running` - list currently running models ([#61](https://github.com/mostlygeek/llama-swap/issues/61))
  - `POST /api/models/unload` - manually unload all running models ([#58](https://github.com/mostlygeek/llama-swap/issues/58))
  - `POST /api/models/unload/:model_id` - unload a specific model
  - `GET /api/profiles` - list configured profiles and the active selection
  - `PUT /api/profiles/active` - activate a profile or select none
  - `/logs` - remote log monitoring
    - `GET /logs` returns buffered plain text logs.
      - If `Accept: text/html` is sent, `/logs` redirects to `/ui/`.
    - `GET /logs/stream` keeps the connection open for live log streaming.
      - Stream endpoints send buffered history first by default; add `?no-history` to stream only new lines.
    - `GET /logs/stream/proxy` streams proxy logs only.
    - `GET /logs/stream/upstream` streams upstream process logs only.
    - `GET /logs/stream/{model_id}` streams logs for one model (including IDs with slashes, like `author/model`).
  - `GET /models/sse` - model load/unload events (**fork**: Zed llama.cpp contract)
  - `/health` - just returns "OK"
  - `/metrics` - system and GPU metrics for prometheus
- ✅ API Key support - define keys to restrict access to API endpoints
- ✅ Customizable
  - Switch model ID routing at runtime with profiles
  - Run concurrent models with a custom DSL swap matrix ([#643](https://github.com/mostlygeek/llama-swap/issues/643))
  - Automatic unloading of models after timeout by setting a `ttl`
  - Docker and Podman support using `cmd` and `cmdStop` together
  - Preload models on startup with `hooks` ([#235](https://github.com/mostlygeek/llama-swap/pull/235))
	  - Apply filters to requests to control inference with `stripParams`, `setParams` and `setParamsByID`
  - ✅ SSE normalization — canonicalize streaming responses to OpenAI `chat.completion.chunk` format
    - Configure per-model with `normalize_sse` or globally with `upstream.normalize_sse`
These changes are **not** in upstream mostlygeek. They make llama-swap a reliable local front door for Zed, OpenFang, and the sovereign stack at `:25100`.

| | Category | Patch | Why | Files |
|-|----------|-------|-----|-------|
| 📡 | **API** | **`GET /models/sse`** | Zed's llama.cpp provider listens for model load/unload events. Real backends often lack this feed; we **synthesize** it from the proxy lifecycle so Zed re-discovers models when swap loads/unloads. | `internal/server/models_sse.go` |
| 📡 | **API** | **SSE normalization** | Some servers emit non-OpenAI chunk shapes; clients (Zed, VS Code, agents) break. Optional global/per-model rewrite to OpenAI `chat.completion.chunk`. | config `upstream.normalize_sse` |
| 📡 | **API** | **Complete SSE loading envelope** | Loading placeholders must look like real OpenAI stream chunks (incl. choice `index`) so clients don't drop the stream. | router / loading writer |
| 📡 | **API** | **Model-event watch fixes** | Unload/load SSE and in-memory state stay consistent when models go missing mid-flight. | `watchModelState`, tests |
| 🔧 | **Reliability** | **IPv4 loopback default** | `localhost` → `::1` first on this host; backends bind IPv4 only → `connection refused`. Defaults use `127.0.0.1`. | `internal/config/model_config.go` |
| 🔧 | **Reliability** | **Free stale port before spawn** | Orphan `llama-server` holds `:2500x` → next load fails. `fuser -k` on the target port before exec. | `internal/process/process_command.go` |
| 🔧 | **Reliability** | **AST Matrix Go port** | Full port of the Python AST Matrix into Go, compiled into the binary. 193 string references, zero external runtime deps. | `internal/astmatrix/` |
| ⚙️ | **Config** | **Filters consolidation** | Dropped broken `ModelFilters` wrapper; legacy `strip_params` YAML still works; `SanitizedCommand` / macro resolution fixed. | `internal/config/*` |

### Sovereign deployment

| Item | Value |
|------|-------|
| Listen | **`http://127.0.0.1:25100`** (`LLAMA_SWAP_PORT`) |
| Chat UI | `http://127.0.0.1:25100/ui/` |
| OpenAI API | `http://127.0.0.1:25100/v1` |
| Binary (symlink) | `/home/toxic/sovereign/tools/llama-swap/llama-swap` → `projects/llama-swap-main/llama-swap` |
| Runtime config | `/home/toxic/sovereign/tools/llama-swap/config.yaml` (sm_86 / RTX 3090 matrix, macros for 4 forks) |
| Model inventory | `tools/llama-swap/MODEL_INVENTORY.md` (local GGUF audit) |
| Orchestration | `mise run up` → process-compose module `llama-swap` |

No vLLM. Backend slots are local `llama-server` builds on `25001–25099`, scheduled by this proxy.

### 🧠 AST Matrix Go Port

The Python AST Matrix (`toxicwind/ast-matrix`) has been fully ported to Go and compiled directly into the `llama-swap` binary.

| Aspect | Detail |
|--------|--------|
| **Location** | `internal/astmatrix/` |
| **Coverage** | 193 string references across all AST visitors, transformers, and matrix operations |
| **Dependencies** | Zero external runtime deps — pure Go standard library |
| **Integration** | Invoked from the swap router to compute optimal model slot assignments from the matrix DSL |
| **Performance** | Eliminates the Python subprocess overhead (~40ms per eval → sub-millisecond) |
| **Source** | Based on `toxicwind/ast-matrix` Python reference, reimplemented in Go for tight coupling with the scheduler |

The port covers:
- **Matrix parser** — DSL → AST with position tracking and error recovery
- **Visitor pattern** — Walk, transform, and query the AST for slot resolution
- **Slot solver** — Given a matrix definition and requested model IDs, compute the minimal set of load/unload operations
- **String table** — All 193 diagnostic/error strings match the Python original, ensuring identical debug output

This is what makes the `matrix` config directive in llama-swap work without shelling out to Python.



### Build

```bash
cd ~/projects/llama-swap-main
go build -o llama-swap .
```

### Remotes

```text
origin  https://github.com/mostlygeek/llama-swap.git   (upstream, read-only)
fork    https://github.com/toxicwind/llama-swap.git    (this repo)
```

---

### Web UI

llama-swap includes a real time web interface with a playground for testing out all sorts of local models:

<img width="1094" height="667" alt="image" src="https://github.com/user-attachments/assets/a79b3cea-5ee1-45f1-8db9-5f5331690e64" />

View detailed token metrics:

<img width="1090" height="672" alt="image" src="https://github.com/user-attachments/assets/145f4ece-af2f-4a45-a3c1-45ae5d3c7e7f" />

Inspect request and responses:

<img width="1078" height="668" alt="image" src="https://github.com/user-attachments/assets/947cda4f-9aa1-4fa5-a550-5c469968c1d9" />

Manually load and unload models:

<img width="1088" height="659" alt="image" src="https://github.com/user-attachments/assets/b6b850f3-c5b0-4c14-ba90-be2de25b51c7" />

Real time log streaming:

<img width="1087" height="668" alt="image" src="https://github.com/user-attachments/assets/9bb0c362-862c-4e68-820c-4c977fc9de4e" />

## Installation

llama-swap can be installed in multiple ways

1. Docker
2. Homebrew (macOS and Linux)
3. MacPorts (macOS)
4. WinGet
5. From release binaries
6. From source

### Docker Install ([download images](https://github.com/mostlygeek/llama-swap/pkgs/container/llama-swap))

Two types of container images are built nightly for llama-swap:

1. A unified container with llama-server, ik-llama-server, stable-diffusion.cpp, whisper.cpp and llama-swap built from source. This is only available for cuda and vulkan but has more capabilities. This one is recommended for use.
2. A legacy image that is based on llama.cpp's images and llama-swap copied into the container. Use this one if you prefer to stay close to llama.cpp's container images.

#### Unified container (Recommended)

```shell
$ docker pull ghcr.io/mostlygeek/llama-swap:unified-cuda

# run with a custom configuration and models directory
$ docker run -it --rm --runtime nvidia -p 9292:8080 \
 -v /path/to/models:/models \
 -v /path/to/custom/config.yaml:/etc/llama-swap/config/config.yaml \
 ghcr.io/mostlygeek/llama-swap:unified-cuda
```

#### Legacy container

```shell
$ docker pull ghcr.io/mostlygeek/llama-swap:cuda

# run with a custom configuration and models directory
$ docker run -it --rm --runtime nvidia -p 9292:8080 \
 -v /path/to/models:/models \
 -v /path/to/custom/config.yaml:/app/config.yaml \
 ghcr.io/mostlygeek/llama-swap:cuda
```

<details>
<summary>
more examples
</summary>

```shell
# pull latest images per platform
docker pull ghcr.io/mostlygeek/llama-swap:cpu
docker pull ghcr.io/mostlygeek/llama-swap:cuda
docker pull ghcr.io/mostlygeek/llama-swap:vulkan
docker pull ghcr.io/mostlygeek/llama-swap:intel
docker pull ghcr.io/mostlygeek/llama-swap:musa

# tagged llama-swap, platform and llama-server version images
docker pull ghcr.io/mostlygeek/llama-swap:v166-cuda-b6795

# non-root cuda
docker pull ghcr.io/mostlygeek/llama-swap:cuda-non-root

```

</details>

### Homebrew Install (macOS/Linux)

```shell
brew tap mostlygeek/llama-swap
brew install llama-swap
llama-swap --config path/to/config.yaml --listen localhost:8080
```

### MacPorts (macOS)

> [!NOTE]
> Maintained by MacPorts community - [llama-swap port](https://ports.macports.org/port/llama-swap). It is not an official part of llama-swap.

```shell
sudo port install llama-swap
llama-swap --config path/to/config.yaml --listen localhost:8080
```

### WinGet Install (Windows)

> [!NOTE]
> WinGet is maintained by community contributor [Dvd-Znf](https://github.com/Dvd-Znf) ([#327](https://github.com/mostlygeek/llama-swap/issues/327)). It is not an official part of llama-swap.

```shell
# install
C:\> winget install llama-swap

# upgrade
C:\> winget upgrade llama-swap
```

### Pre-built Binaries

Binaries are available on the [release](https://github.com/mostlygeek/llama-swap/releases) page for Linux, Mac, Windows and FreeBSD.

### Building from source

1. Building requires Go and Node.js (for UI).
1. `git clone https://github.com/mostlygeek/llama-swap.git`
1. `make clean all`
1. look in the `build/` subdirectory for the llama-swap binary

## Configuration

```yaml
# minimum viable config.yaml

models:
  model1:
    cmd: llama-server --port ${PORT} --model /path/to/model.gguf
```

That's all you need to get started:

1. `models` - holds all model configurations
2. `model1` - the ID used in API calls
3. `cmd` - the command to run to start the server.
4. `${PORT}` - an automatically assigned port number

Almost all configuration settings are optional and can be added one step at a time:

- Advanced features
  - `matrix` to run concurrent models with a custom swap logic DSL
  - `hooks` to run things on startup
  - `macros` reusable snippets
- Model customization
  - `ttl` to automatically unload models
  - `unloadTimeout` to tune graceful unloads (manual, API and `ttl` expiry)
  - `aliases` to use familiar model names (e.g., "gpt-4o-mini")
  - `env` to pass custom environment variables to inference servers
  - `cmdStop` gracefully stop Docker/Podman containers
  - `useModelName` to override model names sent to upstream servers
  - `${PORT}` automatic port variables for dynamic port assignment
  - `filters` rewrite parts of requests before sending to the upstream server

See the [configuration documentation](docs/configuration.md) for all options.

## How does llama-swap work?

When a request is made to an OpenAI compatible endpoint, llama-swap will extract the `model` value and load the appropriate server configuration to serve it. If the wrong upstream server is running, it will be replaced with the correct one. This is where the "swap" part comes in. The upstream server is automatically swapped to handle the request correctly.

In the most basic configuration llama-swap handles one model at a time. For more advanced use cases, using a `matrix` allows multiple models to be loaded at the same time. You have complete control over how your system resources are used.

## Reverse Proxy Configuration (nginx)

If you deploy llama-swap behind nginx, disable response buffering for streaming endpoints. By default, nginx buffers responses which breaks Server‑Sent Events (SSE) and streaming chat completion. ([#236](https://github.com/mostlygeek/llama-swap/issues/236))

Recommended nginx configuration snippets:

```nginx
# SSE for UI events/logs
location /api/events {
    proxy_pass http://your-llama-swap-backend;
    proxy_buffering off;
    proxy_cache off;
}

# Streaming chat completions (stream=true)
location /v1/chat/completions {
    proxy_pass http://your-llama-swap-backend;
    proxy_buffering off;
    proxy_cache off;
}
```

As a safeguard, llama-swap also sets `X-Accel-Buffering: no` on SSE responses. However, explicitly disabling `proxy_buffering` at your reverse proxy is still recommended for reliable streaming behavior.

## Monitoring Logs on the CLI

```sh
# sends up to the last 10KB of logs
$ curl http://host/logs

# streams combined logs
curl -Ns http://host/logs/stream

# stream llama-swap's proxy status logs
curl -Ns http://host/logs/stream/proxy

# stream logs from upstream processes that llama-swap loads
curl -Ns http://host/logs/stream/upstream

# stream logs only from a specific model
curl -Ns http://host/logs/stream/{model_id}

# stream and filter logs with linux pipes
curl -Ns http://host/logs/stream | grep 'eval time'

# appending ?no-history will disable sending buffered history first
curl -Ns 'http://host/logs/stream?no-history'
```

## Do I need to use llama.cpp's server (llama-server)?

Any OpenAI compatible server would work. llama-swap was originally designed for llama-server and it is the best supported.

For Python based inference servers like vllm or tabbyAPI it is recommended to run them via podman or docker. This provides clean environment isolation as well as responding correctly to `SIGTERM` signals for proper shutdown.


---

## AstMatrix V2 — Production-Grade Cloud Provider Router

AstMatrix provides intelligent routing to cloud LLM providers with production-grade reliability.

### Features

- **8 Routing Strategies**: hybrid, ast_race, sticky_affinity, weighted_elo, least_latency, round_robin, free, circuit_chain
- **Circuit Breakers**: Closed→Open→Half-Open with automatic probe recovery
- **Health Probes**: Background 5s checks every 30s
- **Request Coalescing**: Deduplicates identical concurrent requests
- **Streaming SSE**: Proper flush every 32KB for real-time responses
- **Retry with Backoff**: 3 attempts per provider with exponential backoff
- **Rate Limiting**: Token bucket per provider (60/min paid, 10/min free)
- **Latency Tracking**: Exponential moving average per provider
- **Sticky Sessions**: Session affinity via Authorization header
- **Model Mapping**: Map local model IDs to provider-specific IDs

### Built-in Providers (13)

| Provider | Base URL | Free Tier | Models |
|----------|----------|-----------|--------|
| llama-swap | http://127.0.0.1:25100/v1 | ✓ | local-fast, local-quality, local-longctx |
| openrouter | https://openrouter.ai/api/v1 | | openrouter/auto |
| nvidia | https://integrate.api.nvidia.com/v1 | ✓ | llama-3.1-nemotron-70b |
| groq | https://api.groq.com/openai/v1 | ✓ | llama-3.1-70b-versatile |
| together | https://api.together.xyz/v1 | | llama-3.1-70b |
| cerebras | https://api.cerebras.ai/v1 | ✓ | llama-3.1-70b |
| fireworks | https://api.fireworks.ai/inference/v1 | | llama-3.1-70b |
| hyperbolic | https://api.hyperbolic.xyz/v1 | ✓ | llama-3.1-70b |
| github | https://models.inference.ai.azure.com | ✓ | Phi-4, gpt-4o-mini |
| mistral | https://api.mistral.ai/v1 | | mistral-large-2 |
| openai | https://api.openai.com/v1 | | gpt-4o, gpt-4o-mini, o1-preview |
| perplexity | https://api.perplexity.ai | | sonar |
| siliconflow | https://api.siliconflow.cn/v1 | ✓ | deepseek-v2 |

### Configuration

```yaml
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
```

### Status Endpoint

```bash
curl http://localhost:25100/astmatrix/status
curl http://localhost:25100/astmatrix/metrics
```

### Architecture

| File | Purpose |
|------|---------|
| `config.go` | YAML configuration structs |
| `circuit.go` | Circuit breaker with half-open support |
| `coalescer.go` | Request deduplication |
| `metrics.go` | Latency histograms, error rates |
| `providers.go` | Provider registry (13 built-in) |
| `healthdb.go` | SQLite health DB + sticky sessions |
| `ratelimit.go` | Token bucket rate limiter |
| `router.go` | Main HTTP handler (8 strategies) |
| `matrix.go` | Coordinator wrapper |
| `ui.go` | Status/metrics HTTP endpoints |
