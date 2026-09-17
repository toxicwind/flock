# Kimi API Patterns — OSINT Extracted

## Base URLs
- `https://agent-gw.kimi.com/coding/v1` — agent gateway (prod)
- `https://api.kimi.com/coding/v1` — API endpoint
- `https://auth.kimi.com` — OAuth host

## OAuth
- Client ID: `17e5f671-d194-4dfb-9706-5516cb48c098`
- Endpoint: `https://auth.kimi.com`

## Endpoints (OpenAI Compatible)
- `POST /v1/chat/completions` — chat completions
- `POST /v1/messages` — Anthropic compatible
- `POST /v1/tools` — tool invocation
- `POST /v1/mcp/` — MCP protocol

## Headers
- `Authorization: Bearer <sk-kimi-…>`
- `X-Kimi-Chat-Id`
- `X-Msh-*` (device related)

## Models
- `kimi-for-coding` (default, 262144 context)
- `k3-agent`
- `k3-agent-swarm`
- `k2d6-agent`
- `kimi-k2.5`

## Local Paths (Kimi Desktop)
- `~/Library/Application Support/kimi-desktop/`
- `kimi-agent/kimi-work-models-cache.json`
- `daimon-share/daimon/config.json`
- `daimon-share/daimon/runtime/kimi-code/config.toml`
- `daimon-share/daimon/agents/main/runner.state.json` — control WS endpoint + token

## Environment Variables
- `KIMI_BASE_URL=https://agent-gw.kimi.com/coding/`
- `DAIMON_KIMI_MESSAGES_BASE_URL=https://agent-gw.kimi.com/coding`
- `AGENT_GW_MCP_URL=https://agent-gw.kimi.com/coding/v1/mcp/`
- `AGENT_GW_BASE_URL`
- `AGENT_GW_API_KEY`
- `DEFAULT_AI_BASE_URL`
- `DEFAULT_AI_API_KEY`
- `DEFAULT_AI_MODEL`

## Control WebSocket
- `ws://127.0.0.1:<port>/control`
- Token in `runner.state.json`
- Supports `conversations.updateKimiModelList`

## Sources
- `linroger/Atlas-Website` — `api/ai/gateway.ts`
- `A3S-Lab/CLI` — `src/account_providers/kimi.rs`
- `williamdh457/codex-spur` — `docs/kimi-app-phase0-probe.md`
