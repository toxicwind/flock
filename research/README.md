# NVIDIA NIM Inkling API — Compatibility & Latency Research Suite

> **Research-grade tooling for evaluating NVIDIA NIM API compatibility, parameter discovery, and inference latency characterization.**

[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)](https://go.dev)
[![Nuclei](https://img.shields.io/badge/Nuclei-v3-3B82F6?logo=target)](https://nuclei.projectdiscovery.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

This repository provides a comprehensive research toolkit for analyzing the **NVIDIA NIM** inference API, specifically the `thinkingmachines/inkling` model endpoint.

## Quick Start

```bash
export NVIDIA_API_KEY=$(cat .env.keys | grep NVIDIA_API_KEY | cut -d= -f2)

# Single test
cd cmd/benchmark && go run . -effort max -max-tokens 16384

# Parameter discovery
go run . -discover -c 5

# Full benchmark
go run . -benchmark -c 5 -output ../../results
```

## Key Findings

| Parameter | NIM Support | Notes |
|-----------|-------------|-------|
| `max_tokens` | ✅ | Primary output limit (ceiling: 16,384) |
| `max_completion_tokens` | ❌ | Rejected — use `max_tokens` |
| `chat_template_kwargs.reasoning_effort` | ✅ | Valid: none, low, medium, high, max |
| `reasoning_effort` (top-level) | ⚠️ | Accepted but ignored |
| `stream` | ✅ | SSE supported |

### Latency by Reasoning Effort

| Effort | Avg Latency |
|--------|-------------|
| `none` | ~500ms |
| `low` | ~2s |
| `medium` | ~3s |
| `high` | ~5s |
| `max` | ~20s+ |

### Edge Case: `reasoning_tokens: null`

When `reasoning_effort=none`, the API returns `null` for `reasoning_tokens`. Strict-typed clients (Rust/serde) may crash with `invalid type: null, expected u32`.

**Fix**: Use `reasoning_effort: "max"` or handle nullable fields.

## Model Specs

| Spec | Value |
|------|-------|
| Model ID | `thinkingmachines/inkling` |
| Architecture | 975B MoE (41B active) |
| Context Window | 1,048,576 tokens |
| Max Output (NIM) | 16,384 tokens |
| Layers | 66 |
| Experts | 256 routed + 2 shared |

## License

MIT
