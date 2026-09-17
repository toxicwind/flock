#!/usr/bin/env python3
"""NVIDIA NIM benchmark runner with catalog + live availability probe.

Pipeline:
  1) GET /v1/models → cache → filter chat candidates
  2) probe each candidate (tiny non-stream chat call)
  3) full benchmark only AVAILABLE models (unless SKIP_PROBE / BENCH_ALL)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db_utils import write_run  # noqa: E402
from model_catalog import get_benchmark_models  # noqa: E402
from model_probe import (  # noqa: E402
    STATUS_AVAILABLE,
    STATUS_ERROR,
    STATUS_GONE,
    STATUS_RATE_LIMITED,
    STATUS_TIMEOUT,
    STATUS_UNAUTHORIZED,
    classify_http_error,
    probe_models,
    save_availability_cache,
    summarize_probes,
)

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
OUTPUT_FILE = SCRIPT_DIR / "results.json"
AVAIL_OUT = SCRIPT_DIR / "availability_cache.json"


def _load_dotenv() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

API_BASE = os.getenv("API_BASE", "https://integrate.api.nvidia.com/v1")
API_KEY = os.getenv("NIM_API_KEY") or os.getenv("NVIDIA_API_KEY") or ""
MODEL_GROUP = os.getenv("MODEL_GROUP", "all")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))
PROMPT = os.getenv(
    "BENCH_PROMPT",
    "Write a Python function that checks if a number is prime and returns True or False",
)
STATIC_MODELS = [m.strip() for m in os.getenv("STATIC_MODELS", "").split(",") if m.strip()]
SKIP_PROBE = os.getenv("SKIP_PROBE", "").lower() in {"1", "true", "yes"}
PROBE_ONLY = os.getenv("PROBE_ONLY", "").lower() in {"1", "true", "yes"}
# Default: only full-bench AVAILABLE models
BENCH_ONLY_AVAILABLE = os.getenv("BENCH_ONLY_AVAILABLE", "1").lower() not in {"0", "false", "no"}


def resolve_candidates() -> tuple[list[str], dict[str, Any]]:
    if STATIC_MODELS:
        print(f"[test_models] Using STATIC_MODELS ({len(STATIC_MODELS)})")
        models = list(STATIC_MODELS)
        meta = {
            "source": "static",
            "total_catalog": len(models),
            "chat_count": len(models),
            "testing_count": len(models),
        }
    else:
        models, meta = get_benchmark_models(api_key=API_KEY, verbose=True)
        print(
            f"[test_models] Catalog source={meta['source']} "
            f"testing={len(models)} chat_pool={meta.get('chat_count')} "
            f"catalog={meta['total_catalog']}"
        )

    if MODEL_GROUP == "group1":
        half = len(models) // 2 + len(models) % 2
        models = models[:half]
    elif MODEL_GROUP == "group2":
        half = len(models) // 2 + len(models) % 2
        models = models[half:]
    return models, meta


def to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _parse_http_error_body(error_body: str, status_code: int) -> str:
    for line in error_body.splitlines():
        if line.strip().startswith("data: ") and line.strip()[6:] != "[DONE]":
            try:
                err_chunk = json.loads(line.strip()[6:])
                err_obj = err_chunk.get("error")
                if isinstance(err_obj, dict):
                    return f"HTTP {status_code}: {err_obj.get('message', '')}"
                if isinstance(err_obj, str):
                    return f"HTTP {status_code}: {err_obj}"
            except json.JSONDecodeError:
                pass
            break
    try:
        err_data = json.loads(error_body)
        err_obj = err_data.get("error") or err_data.get("detail") or err_data.get("title")
        if isinstance(err_obj, dict):
            return f"HTTP {status_code}: {err_obj.get('message', err_obj)}"
        if isinstance(err_obj, str):
            # include detail if present
            detail = err_data.get("detail")
            if err_data.get("title") and detail and err_obj == err_data.get("title"):
                return f"HTTP {status_code}: {err_obj}: {detail}"
            return f"HTTP {status_code}: {err_obj}"
        if error_body:
            return f"HTTP {status_code}: {error_body[:200]}"
    except (json.JSONDecodeError, AttributeError):
        if error_body:
            return f"HTTP {status_code}: {error_body[:200]}"
    return f"HTTP {status_code}"


def result_template(
    model: str,
    *,
    success: bool,
    status: str,
    error: str | None = None,
    response_time: int | None = None,
    tokens_generated: int | None = None,
    total_tokens: int | None = None,
    ttft: int | None = None,
    response: str | None = None,
    phase: str = "benchmark",
) -> dict[str, Any]:
    return {
        "model": model,
        "success": success,
        "status": status,
        "available": status == STATUS_AVAILABLE and success if phase == "benchmark" else status == STATUS_AVAILABLE,
        "phase": phase,
        "error": error,
        "responseTime": response_time,
        "tokensGenerated": tokens_generated,
        "totalTokens": total_tokens,
        "timeToFirstToken": ttft,
        "response": response,
    }


def call_model(model: str, prompt: str) -> dict[str, Any]:
    """Full streaming benchmark call."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": int(os.getenv("BENCH_MAX_TOKENS", "150")),
        "stream": True,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE.rstrip('/')}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )

    started = time.perf_counter()
    status_code = 0
    error_body = ""

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status_code = response.status
            content_parts: list[str] = []
            time_to_first_token_ms: int | None = None
            completion_tokens = 0
            total_tokens = 0

            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[len("data: ") :]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices")
                if isinstance(choices, list) and choices:
                    delta = choices[0].get("delta") or {}
                    text = (
                        delta.get("content")
                        or delta.get("reasoning_content")
                        or delta.get("reasoning")
                        or ""
                    )
                    if not text:
                        msg = choices[0].get("message") or {}
                        text = (
                            msg.get("content")
                            or msg.get("reasoning_content")
                            or msg.get("reasoning")
                            or ""
                        )
                    if text:
                        if time_to_first_token_ms is None:
                            time_to_first_token_ms = int((time.perf_counter() - started) * 1000)
                        content_parts.append(text)

                usage = chunk.get("usage") if isinstance(chunk.get("usage"), dict) else {}
                if usage:
                    completion_tokens = to_int(usage.get("completion_tokens")) or completion_tokens
                    total_tokens = to_int(usage.get("total_tokens")) or total_tokens

            response_time = int((time.perf_counter() - started) * 1000)
            content = "".join(content_parts)

    except urllib.error.HTTPError as exc:
        status_code = getattr(exc, "code", 0) or 0
        error_body = exc.read().decode("utf-8", errors="replace")
        response_time = int((time.perf_counter() - started) * 1000)
        msg = _parse_http_error_body(error_body, status_code)
        status = classify_http_error(status_code, msg)
        return result_template(
            model,
            success=False,
            status=status,
            error=msg,
            response_time=response_time,
            phase="benchmark",
        )
    except TimeoutError:
        return result_template(
            model,
            success=False,
            status=STATUS_TIMEOUT,
            error=f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s",
            phase="benchmark",
        )
    except Exception as exc:
        msg = str(exc)
        status = STATUS_TIMEOUT if "timed out" in msg.lower() else STATUS_ERROR
        return result_template(
            model,
            success=False,
            status=status,
            error=f"Request failed: {exc}",
            phase="benchmark",
        )

    if status_code >= 400:
        msg = _parse_http_error_body(error_body, status_code)
        status = classify_http_error(status_code, msg)
        return result_template(
            model,
            success=False,
            status=status,
            error=msg,
            response_time=int((time.perf_counter() - started) * 1000),
            phase="benchmark",
        )

    if not content.strip():
        return result_template(
            model,
            success=False,
            status=STATUS_ERROR,
            error="No content in response",
            response_time=response_time,
            phase="benchmark",
        )

    return result_template(
        model,
        success=True,
        status=STATUS_AVAILABLE,
        response_time=response_time,
        tokens_generated=completion_tokens,
        total_tokens=total_tokens,
        ttft=time_to_first_token_ms,
        response=content,
        phase="benchmark",
    )


def compile_output(
    timestamp: str,
    prompt: str,
    models: list[dict[str, Any]],
    *,
    catalog_meta: dict[str, Any],
    probe_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    successful = [item for item in models if item.get("success")]
    bench_models = [m for m in models if m.get("phase") == "benchmark"]
    success_count = len(successful)
    total_bench = len(bench_models) if bench_models else len(models)

    if successful:
        fastest = min(
            successful,
            key=lambda item: item.get("responseTime")
            if isinstance(item.get("responseTime"), int)
            else float("inf"),
        )
        fastest_model = fastest.get("model", "N/A")
        fastest_time = fastest.get("responseTime", 0) or 0
    else:
        fastest_model = "N/A"
        fastest_time = 0

    status_counts: dict[str, int] = {}
    for m in models:
        st = m.get("status") or ("AVAILABLE" if m.get("success") else "ERROR")
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "timestamp": timestamp,
        "prompt": prompt,
        "models": models,
        "catalog": catalog_meta,
        "probe": probe_summary,
        "summary": {
            "successCount": success_count,
            "totalModels": total_bench,
            "fastestModel": fastest_model,
            "fastestTime": fastest_time,
            "byStatus": status_counts,
            "nvidiaCatalog": catalog_meta.get("total_catalog"),
            "chatCandidates": catalog_meta.get("chat_count") or catalog_meta.get("testing_count"),
            "liveCallable": (probe_summary or {}).get("available_count"),
            "unavailableGone": status_counts.get(STATUS_GONE, 0),
            "unauthorized": status_counts.get(STATUS_UNAUTHORIZED, 0),
            "rateLimited": status_counts.get(STATUS_RATE_LIMITED, 0),
            "timeouts": status_counts.get(STATUS_TIMEOUT, 0),
            "errors": status_counts.get(STATUS_ERROR, 0),
        },
    }


def update_history(new_run: dict[str, Any]) -> None:
    # History remains success-oriented; include unavailable rows as failed for trends.
    write_run(new_run)
    print(f"History updated: {ROOT_DIR / 'history.db'}")


def main() -> int:
    if not API_KEY:
        print(
            "Error: NIM_API_KEY / NVIDIA_API_KEY not set (or missing in .env)",
            file=sys.stderr,
        )
        return 1

    candidates, catalog_meta = resolve_candidates()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    group_label = f" (Group: {MODEL_GROUP})" if MODEL_GROUP else ""
    print(f"Starting NVIDIA NIM Model Benchmarks{group_label}...")
    print(f"Timestamp: {timestamp}")
    print(f"Chat candidates: {len(candidates)}")
    print()

    probe_summary: dict[str, Any] | None = None
    probe_by_model: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    # --- Phase 1: live availability probe ---
    if not SKIP_PROBE:
        print("=== Phase 1: availability probe ===")
        probes = probe_models(candidates, api_key=API_KEY, verbose=True)
        probe_summary = summarize_probes(probes)
        save_availability_cache(probes, catalog_meta=catalog_meta, path=AVAIL_OUT)
        for p in probes:
            probe_by_model[p.model] = p.to_dict()

        print()
        print(
            f"Probe summary: available={probe_summary['available_count']}/"
            f"{probe_summary['total_probed']} by_status={probe_summary['by_status']}"
        )
        print(f"Availability cache → {AVAIL_OUT.name}")
        print()

        if PROBE_ONLY:
            # Emit probe-only results file
            for p in probes:
                results.append(
                    result_template(
                        p.model,
                        success=False,
                        status=p.status,
                        error=None if p.available else p.error,
                        response_time=p.latency_ms,
                        response=p.detail if p.available else None,
                        phase="probe",
                    )
                )
                # mark available probes as success=False for history? keep success only for real bench
                if p.available:
                    results[-1]["available"] = True

            final_json = compile_output(
                timestamp, PROMPT, results, catalog_meta=catalog_meta, probe_summary=probe_summary
            )
            # For probe-only, successCount should reflect live callable
            final_json["summary"]["successCount"] = probe_summary["available_count"]
            final_json["summary"]["totalModels"] = probe_summary["total_probed"]
            OUTPUT_FILE.write_text(json.dumps(final_json, indent=2), encoding="utf-8")
            print(f"PROBE_ONLY complete. Live callable: {probe_summary['available_count']}")
            print(f"Results saved to {OUTPUT_FILE.name}")
            _print_fleet_summary(final_json)
            return 0
    else:
        print("[test_models] SKIP_PROBE=1 — treating all candidates as AVAILABLE")

    # --- Phase 2: full benchmark ---
    print("=== Phase 2: full benchmark ===")
    to_bench: list[str]
    if SKIP_PROBE:
        to_bench = candidates
    elif BENCH_ONLY_AVAILABLE:
        to_bench = [m for m in candidates if probe_by_model.get(m, {}).get("available")]
        # Record unavailable probes into results (not as benchmark failures noise)
        for m in candidates:
            pr = probe_by_model.get(m)
            if not pr:
                continue
            if not pr.get("available"):
                results.append(
                    result_template(
                        m,
                        success=False,
                        status=pr.get("status") or STATUS_GONE,
                        error=pr.get("error"),
                        response_time=pr.get("latency_ms"),
                        phase="probe",
                    )
                )
    else:
        to_bench = candidates

    print(f"Benchmarking {len(to_bench)} available model(s)...")
    print()

    for model in to_bench:
        print(f"Benchmarking: {model}")
        result = call_model(model, PROMPT)
        if result.get("success"):
            ttft_str = (
                f", TTFT {result['timeToFirstToken']}ms"
                if result.get("timeToFirstToken") is not None
                else ""
            )
            print(
                f"  ✓ Success ({result['responseTime']}ms{ttft_str}, "
                f"{result.get('tokensGenerated', 0)} tokens)"
            )
        else:
            print(f"  ✗ {result.get('status')}: {result.get('error') or 'Unknown error'}")
        results.append(result)
        time.sleep(float(os.getenv("BENCH_SLEEP_SECONDS", "0.5")))

    print()
    print("Compiling results...")
    final_json = compile_output(
        timestamp, PROMPT, results, catalog_meta=catalog_meta, probe_summary=probe_summary
    )
    OUTPUT_FILE.write_text(json.dumps(final_json, indent=2), encoding="utf-8")

    bench_ok = final_json["summary"]["successCount"]
    bench_total = len([m for m in results if m.get("phase") == "benchmark"])
    print(f"Results saved to {OUTPUT_FILE.name}")
    print(f"Benchmark: {bench_ok}/{bench_total} successful among attempted")
    _print_fleet_summary(final_json)

    skip_history = os.getenv("SKIP_HISTORY", "").lower() in {"1", "true", "yes"}
    if MODEL_GROUP == "all" and not skip_history and not PROBE_ONLY:
        # Prefer writing only benchmark phase rows + optional unavailable markers
        update_history(final_json)

    # Exit non-zero only on hard runner failures (no candidates), not on fleet unavailability
    if not candidates:
        return 2
    return 0


def _print_fleet_summary(final_json: dict[str, Any]) -> None:
    s = final_json.get("summary") or {}
    print()
    print("=== Fleet snapshot ===")
    print(f"  NVIDIA catalog:        {s.get('nvidiaCatalog')}")
    print(f"  Chat candidates:       {s.get('chatCandidates')}")
    print(f"  Live callable:         {s.get('liveCallable')}")
    print(f"  Unavailable / retired: {s.get('unavailableGone')}")
    print(f"  Permission restricted: {s.get('unauthorized')}")
    print(f"  Rate limited:          {s.get('rateLimited')}")
    print(f"  Timeout:               {s.get('timeouts')}")
    print(f"  Other errors:          {s.get('errors')}")
    print(f"  Benchmark successes:   {s.get('successCount')}/{s.get('totalModels')}")


if __name__ == "__main__":
    raise SystemExit(main())
