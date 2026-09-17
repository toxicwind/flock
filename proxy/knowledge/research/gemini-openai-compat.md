---
type: Research
title: Gemini API via OpenAI-compatible endpoint
description: Externally validated facts for wiring Gemini as an OpenAI-compatible backend.
date: 2026-09-17
source: https://ai.google.dev/gemini-api/docs/openai
---

# Gemini API — OpenAI compatibility

Gemini exposes an OpenAI-compatible Chat Completions endpoint. Any OpenAI
client library works with three changes.

## Endpoint

- Base URL: `https://generativelanguage.googleapis.com/v1beta/openai/`
- Chat completions: `POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`
- Auth: `Authorization: Bearer $GEMINI_API_KEY` (key from Google AI Studio)

## Client migration (3 lines)

```python
from openai import OpenAI
client = OpenAI(
    api_key="GEMINI_API_KEY",                    # 1. Gemini key, not OpenAI key
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",  # 2. Gemini base
)
response = client.chat.completions.create(
    model="gemini-3.6-flash",                    # 3. Gemini model id
    messages=[{"role": "user", "content": "Explain how AI works"}],
)
```

```bash
curl "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GEMINI_API_KEY" \
  -d '{"model": "gemini-3.6-flash",
       "messages": [{"role": "user", "content": "Explain how AI works"}]}'
```

## Supported models (Chat Completions API)

Gemini 3.5 Flash, 3.1 Flash-Lite, 3.1 Pro preview, 3 Flash preview,
2.5 Pro, 2.5 Flash / Flash preview. Plus select self-deployed Model Garden
models via HF TGI / vLLM containers (gemma-2-9b/27b-it, Llama-3.1-8B, Mistral-7B, Mistral Nemo).

## Reasoning mapping

| OpenAI `reasoning_effort` | Gemini 3.1 Pro / 3 Flash `thinking_level` | Gemini 2.5 `thinking_budget` |
|---|---|---|
| (none) | model default | model default |
| low | low | 1,024 |
| medium | medium | 8,192 |
| high | high | 24,576 |
| none | n/a (2.5 only) | disabled |

Reasoning cannot be turned off for Gemini 2.5 Pro or 3.x models.

## Implications for nim_proxy (mesh)

- Gemini is a drop-in OpenAI-shape backend: same request/response schema as
  the proxy already speaks. A Gemini lane needs only base_url + key routing,
  no schema translation.
- Free-tier note: Gemini API has a no-cost tier in AI Studio (rate-limited);
  verify current quotas before depending on it for the reactive loop.
- Standing scope note (2026-09-14): NIM proxy is designated exclusively for
  NIM/NVIDIA; non-NVIDIA providers belong to Herd. A Gemini lane in
  nim_proxy would be a deliberate scope change — recorded here as research,
  not implemented.
