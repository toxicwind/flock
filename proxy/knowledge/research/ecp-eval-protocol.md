---
type: Research
title: ECP — Evaluation Context Protocol
description: Portable evaluation contract for AI agents (JSON-RPC); spec + reference implementation.
date: 2026-09-17
source: https://github.com/evaluation-context-protocol/ecp / https://arxiv.org/abs/2608.19263
---

# ECP — Evaluation Context Protocol

Vendor-neutral, portable **evaluation contract layer** for agentic systems.
Where MCP standardized tool *execution*, ECP standardizes *evaluation* of
those executions: a small JSON-RPC interface over which an agent exposes its
user-visible output, the tool calls it made, and evaluator-safe audit
context, against which programmatic checks run uniformly across frameworks
and CI systems.

Status (2026-09): early-stage, experimental, open-source. Adapters exist for
LangChain, LlamaIndex, CrewAI, PydanticAI. Python reference runtime + SDK,
early TypeScript SDK, conformance harness, JSON schemas.

## Core concepts

- **Manifest** (`manifest.yaml`): declares scenarios, the agent target
  (command for stdio transport, or `http://127.0.0.1:8765/ecp`), graders.
- **Run**: `ecp run --manifest manifest.yaml [--json] [--json-out report.json] [--report report.html] [--audit-out ecp_audit.json]`
- **Conformance**: `ecp conformance --target "python agent.py"`; `ecp doctor`; `ecp validate manifest.yaml`
- **Agent SDK**: `@on_step` / `@on_reset` decorators (sync or `async def`);
  steps return `Result(public_output=..., usage={"input_tokens","output_tokens","total_tokens"})`.

## Execution boundaries (graceful degradation, not abort)

- `--timeout` / `ECP_RPC_TIMEOUT` (default 30s): bounds a single RPC.
- `--max-duration` / `ECP_MAX_DURATION`: bounds the whole run (a hung agent
  must never pin a CI job).
- On breach/crash/protocol violation: the failing step is recorded **failed**,
  remaining steps in that scenario are **skipped**, next scenario starts with
  a **fresh agent**. A step that never answered counts as a failed `execution`
  check — a timeout can never be mistaken for a pass.

## Audit record

Every run emits structured telemetry: run id, timestamps, manifest SHA-256
digest, agent metadata, configured limits, per-step latency + `exit_reason`
(ok/failed/skipped), aggregated token usage, pass/fail totals. Embedded under
`audit` in the JSON report; standalone via `--audit-out`. Compare
`steps_planned` vs `steps_executed` to spot degraded runs. Schema:
`schema/audit.schema.json`.

## Relevance to our stack

- Our refusal-storm forensics already produce per-step anomaly rows
  (parquet ledger, digests, latencies). ECP's audit record is the same shape
  with a portable schema — adopting its manifest/audit format would make our
  agent evaluations CI-runnable and framework-portable.
- The "degrade, don't abort" boundary model matches our watchdog posture
  (fix-forward, never terminal-stop benign work).
- Fit: evaluation harness for super-ralph / herd agents. Not a nim_proxy
  runtime concern — recorded here because nim_proxy is the mesh's documented
  research surface.

## Adjacent ECPs (name collision, not the same project)

- **Efficient Context Protocol** (efficientlabs-ai/efficient-context-protocol):
  vendor-neutral file architecture for agent workspaces (manifests, context
  compiler, concurrency leases, compaction-resistant ledgers). MIT, zero deps.
- **Engram Context Protocol** (mechtar-ru/engram, ECP v0.1): wire format for
  structured context packets between AI coding tools.
