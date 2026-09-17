import time
import json
from typing import Any, Generator, Iterator
import urllib.request
import urllib.error

from .keypool import FlockKeyPool, parse_retry_after_ms, split_keys

DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class NimError(Exception):
    def __init__(self, message: str, status: int = 0, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class FlockClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        if not api_key:
            raise ValueError(
                "FlockClient requires an api_key. Get yours free at https://build.nvidia.com"
            )
        keys = split_keys(api_key)
        if not keys:
            raise ValueError(
                "FlockClient requires an api_key. Get yours free at https://build.nvidia.com"
            )
        self.api_keys = keys
        self.api_key = keys[0]
        self._pool = FlockKeyPool(keys)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _headers(self, api_key: str | None = None) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key or self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self, path: str, body: dict[str, Any] | None = None, method: str = "POST"
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        data = json.dumps(body or {}).encode("utf-8") if method != "GET" else None
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            key = self._pool.next_available()
            if key is None:
                wait_until = self._pool.earliest_retry_at()
                wait_s = (
                    self.retry_delay
                    if wait_until is None
                    else max(0.0, wait_until - time.time())
                )
                time.sleep(wait_s)
                key = self._pool.next_available()
            if key is None:
                raise last_error or NimError("All API keys are rate limited", 429, True)
            active_key = key
            rotated = attempt > 0 and len(self.api_keys) > 1

            if attempt > 0 and not rotated:
                time.sleep(self.retry_delay * (2 ** (attempt - 1)))

            req = urllib.request.Request(
                url,
                data=data,
                headers=self._headers(active_key),
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    self._pool.record_success(active_key)
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body_text = e.read().decode("utf-8", errors="ignore")
                retryable = e.code in RETRYABLE_STATUS_CODES
                last_error = NimError(
                    f"NIM API error {e.code}: {body_text}", e.code, retryable
                )
                if e.code == 429:
                    self._pool.record_rate_limit(
                        active_key, parse_retry_after_ms(e.headers.get("Retry-After"))
                    )
                else:
                    self._pool.record_failure(active_key, f"HTTP {e.code}")
                if not retryable or attempt >= self.max_retries:
                    raise last_error from e
            except TimeoutError as e:
                last_error = NimError(
                    f"Request timed out after {self.timeout}s", 408, True
                )
                if attempt >= self.max_retries:
                    raise last_error from e

        raise last_error or NimError("Max retries exceeded")

    def stream(
        self, path: str, body: dict[str, Any]
    ) -> Generator[dict[str, Any], None, None]:
        url = f"{self.base_url}{path}"
        payload = {**body, "stream": True}
        data = json.dumps(payload).encode("utf-8")
        headers = {**self._headers(), "Accept": "text/event-stream"}

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

    def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        top_p: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.request(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                **kwargs,
            },
        )

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        yield from self.stream(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs,
            },
        )

    def embed(
        self,
        model: str,
        input_text: str | list[str],
        input_type: str = "query",
        truncate: str = "END",
    ) -> dict[str, Any]:
        return self.request(
            "/embeddings",
            {
                "model": model,
                "input": input_text,
                "input_type": input_type,
                "truncate": truncate,
            },
        )

    def list_models(self) -> dict[str, Any]:
        return self.request("/models", method="GET")

    def probe_model(self, model: str) -> bool:
        """Dead-model guard: True when the model is listed as available."""
        try:
            catalog = self.list_models()
            return any(m.get("id") == model for m in catalog.get("data", []))
        except Exception:
            return False

    def rerank(
        self,
        model: str,
        query: str,
        passages: list[str],
        truncate: str = "END",
    ) -> dict[str, Any]:
        return self.request(
            "/ranking",
            {
                "model": model,
                "query": query,
                "passages": [{"text": p} for p in passages],
                "truncate": truncate,
            },
        )
