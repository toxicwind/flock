## mcp-stack — SSE Gateway for stdio MCP Servers

This subproject provides a canonical Server-Sent Events (SSE) gateway that multiplexes multiple
stdio-based MCP servers behind a single HTTP surface, with discovery, profiles, sidecar resolution,
and basic observability.

### Transport Surface

- `GET /servers` — JSON by default; simple HTML when `Accept: text/html`.
- `GET /servers/:name/info` — per-server info/state.
- `GET /servers/:name/sse` — SSE stream; lazy-spawns the stdio server on first connect.
- `POST /servers/:name/send` — send a JSON line to the stdio server stdin (client→server).
- `GET /.well-known/mcp-servers.json` — live discovery manifest.
- `GET /healthz`, `GET /readyz` — observability endpoints.

### Included Servers (registry entries)

filesystem, readweb, screenshot, playwright, curl (with FlareSolverr), searxng. These entries are
present in the registry; most are disabled by default unless configured. A demo server (`demo`) is
provided for smoke testing.

### Configuration

- `PROFILE`: `dev` (default) or `prod`
- `PORT_HTTP`: fixed port for HTTP/SSE
- `PORT_RANGE_START` / `PORT_RANGE_END`: probe for free port in range
- `SEARXNG_ENGINE_URL`, `FLARESOLVERR_URL`: sidecar resolution
- `WORKSPACE_ALLOWLIST`: comma-separated patterns passed to servers (future)
- `MAX_CONCURRENCY`: numeric, per-server soft limit (future)
- `LOG_LEVEL`: `debug|info|warn|error` (default `info`)
- `HEALTH_TIMEOUT_MS`: health probe timeout (default `10000`)

### Quick start

```bash
node mcp-stack/gateway/server.mjs
# or
PROFILE=dev PORT_HTTP=0 node mcp-stack/gateway/server.mjs

# Visit the printed URL, or e.g.:
curl -N http://localhost:<port>/servers/demo/sse
```

### Tests

```bash
node mcp-stack/tests/smoke.mjs
```
