"""FlockKeyPool — multi-key rotation with 429/Retry-After tracking.

Python mirror of the TypeScript flock-client keypool: keys are deduplicated
on registration, rotation is round-robin over keys whose rate limit has
expired, and a 429 parks the offending key for the server's Retry-After
(default 60s). Key values never appear in stats or error labels.
"""

from __future__ import annotations

import time
from email.utils import parsedate_to_datetime

DEFAULT_RETRY_AFTER_MS = 60_000


def split_keys(raw: "str | list[str] | None") -> list[str]:
    items = raw if isinstance(raw, list) else (raw.split(",") if raw else [])
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip()
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def parse_retry_after_ms(value: "str | None") -> int:
    if not value:
        return DEFAULT_RETRY_AFTER_MS
    value = value.strip()
    try:
        secs = float(value)
        if secs >= 0:
            return int(secs * 1000)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        return max(0, int(dt.timestamp() * 1000 - time.time() * 1000))
    except (ValueError, TypeError):
        return DEFAULT_RETRY_AFTER_MS


class FlockKeyPool:
    def __init__(self, keys: "list[str]"):
        seen: set[str] = set()
        self._keys: list[dict] = []
        for raw in keys:
            key = raw.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            self._keys.append(
                {
                    "key": key,
                    "success_count": 0,
                    "failure_count": 0,
                    "rate_limit_count": 0,
                    "rate_limited_until": None,
                    "last_failure_reason": None,
                }
            )
        self._cursor = 0

    @property
    def size(self) -> int:
        return len(self._keys)

    @staticmethod
    def _limited(state: dict, now: float) -> bool:
        until = state["rate_limited_until"]
        return until is not None and until > now

    def next_available(self) -> "str | None":
        now = time.time()
        for i in range(len(self._keys)):
            idx = (self._cursor + i) % len(self._keys)
            if not self._limited(self._keys[idx], now):
                self._cursor = (idx + 1) % len(self._keys)
                return self._keys[idx]["key"]
        return None

    def _find(self, key: str) -> "dict | None":
        for s in self._keys:
            if s["key"] == key:
                return s
        return None

    def record_success(self, key: str) -> None:
        s = self._find(key)
        if s:
            s["success_count"] += 1
            s["rate_limited_until"] = None
            s["last_failure_reason"] = None

    def record_failure(self, key: str, reason: str) -> None:
        s = self._find(key)
        if s:
            s["failure_count"] += 1
            s["last_failure_reason"] = reason

    def record_rate_limit(self, key: str, retry_after_ms: "int | None" = None) -> None:
        s = self._find(key)
        if s:
            s["rate_limit_count"] += 1
            s["last_failure_reason"] = "Rate limited (429)"
            s["rate_limited_until"] = time.time() + (
                retry_after_ms if retry_after_ms is not None else DEFAULT_RETRY_AFTER_MS
            ) / 1000.0

    def earliest_retry_at(self) -> "float | None":
        times = [s["rate_limited_until"] for s in self._keys if s["rate_limited_until"] is not None]
        return min(times) if times else None

    def get_stats(self) -> list[dict]:
        now = time.time()
        return [
            {
                "label": f"key#{i + 1}",
                "success_count": s["success_count"],
                "failure_count": s["failure_count"],
                "rate_limit_count": s["rate_limit_count"],
                "rate_limited_until": s["rate_limited_until"],
                "is_rate_limited": self._limited(s, now),
                "is_available": not self._limited(s, now),
                "last_failure_reason": s["last_failure_reason"],
            }
            for i, s in enumerate(self._keys)
        ]
