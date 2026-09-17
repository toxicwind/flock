#!/usr/bin/env python3
"""Kimi AgentGW Client Module with Transport Modifications."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__version__ = "1.0.0"

class APIError(Exception):
    def __init__(self, msg: str, status_code: int = 0, body: Any = None, request_id: str = None):
        super().__init__(msg)
        self.status_code, self.body, self.request_id = status_code, body, request_id

class AuthError(APIError): pass

BASE_URL, TIMEOUT = "https://agent-gw-dev.dev.kimi.team/coding", 30.0
USER_AGENT, CONFIG_FILE = f"Kimi AgentGW PySDK/{__version__}", Path("~/.kimi/agent-gw.json")

def _load_config() -> Dict[str, Any]:
    p = CONFIG_FILE.expanduser()
    return json.loads(p.read_text("utf-8")) if p.is_file() else {}

def _resolve_key(explicit: str, cfg: Mapping[str, Any]) -> str:
    if explicit: return explicit
    env = os.environ.get("KIMI_API_KEY")
    if env and env.strip(): return env.strip()
    val = cfg.get("api_key")
    if isinstance(val, str) and val.strip(): return val.strip()
    raise ValueError("Missing API key.")

def _resolve_url(explicit: str, cfg: Mapping[str, Any]) -> str:
    if explicit: return explicit
    env = os.environ.get("KIMI_BASE_URL")
    if env and env.strip(): return env.strip()
    val = cfg.get("base_url")
    return val.strip() if isinstance(val, str) and val.strip() else BASE_URL

class ToolResponse:
    __slots__ = ("raw",)
    def __init__(self, raw: Any):
        if isinstance(raw, Mapping):
            self.raw = dict(raw)
        elif isinstance(raw, str):
            self.raw = {"is_success": True, "result": {"user": [{"text": raw}]}}
        else:
            self.raw = {"is_success": True, "result": {"user": [{"text": json.dumps(raw, ensure_ascii=False)}]}}

    @property
    def is_success(self) -> bool:
        return bool(self.raw.get("is_success")) if "is_success" in self.raw else not self.raw.get("error")

    @property
    def text(self) -> str:
        u = self.raw.get("result", {}).get("user", [])
        return u[0].get("text", "") or "" if u and isinstance(u[0], Mapping) else ""

    def json(self) -> Any:
        t = self.text
        return json.loads(t) if t else (self.raw if "result" not in self.raw else None)

class ToolsAPI:
    def __init__(self, client: "AgentGwClient"):
        self._client = client

    def invoke(self, method: str, params: dict = None, *, timeout: float = None) -> ToolResponse:
        return ToolResponse(self._client._post_json("/v1/tools", {"method": method, "params": dict(params or {})}, timeout=timeout))

    def stock_realtime_price(self, ticker: str, *, time: str, type: str = "realtime_price", file_path: str = None, timeout: float = None) -> ToolResponse:
        p = {"ticker": ticker, "time": time, "type": type}
        if file_path: p["file_path"] = file_path
        return self.invoke("get_stock_realtime_price", p, timeout=timeout)

class AgentGwClient:
    def __init__(
        self,
        api_key: str = None,
        *,
        base_url: str = None,
        timeout: float = TIMEOUT,
        skill: str = None,
        chat_id: str = None,
        user_agent: str = None,
        session: requests.Session = None,
    ):
        cfg = _load_config()
        self.api_key, self.base_url = _resolve_key(api_key, cfg), _resolve_url(base_url, cfg)
        self.timeout, self.skill, self.chat_id, self.user_agent = float(timeout), skill, chat_id, user_agent or USER_AGENT

        if session is None:
            self._session = requests.Session()
            r = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
            a = HTTPAdapter(max_retries=r, pool_connections=10, pool_maxsize=20)
            self._session.mount("https://", a)
            self._session.mount("http://", a)
        else:
            self._session = session
        self.tools = ToolsAPI(self)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "AgentGwClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _headers(self, extra: dict = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.skill: h["X-Kimi-Skill"] = self.skill
        if self.chat_id: h["X-Kimi-Chat-Id"] = self.chat_id
        if extra: h.update(extra)
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        params: dict = None,
        headers: dict = None,
        timeout: float = None,
        stream: bool = False,
    ) -> requests.Response:
        url = self.base_url + path if path.startswith("/") else f"{self.base_url}/{path}"
        h = self._headers(headers)
        if files is not None: h.pop("Content-Type", None)
        try:
            resp = self._session.request(
                method, url, json=json, data=data, files=files, params=params, headers=h,
                timeout=timeout if timeout is not None else self.timeout, stream=stream
            )
        except requests.exceptions.RequestException as e:
            raise APIError(f"Transport error {method} {path}: {e}") from e
        if resp.status_code >= 400: self._raise(resp)
        return resp

    def _post_json(self, path: str, body: Any, *, timeout: float = None) -> Any:
        resp = self._request("POST", path, json=body, timeout=timeout)
        return resp.json() if resp.status_code != 204 and resp.content else None

    def _raise(self, resp: requests.Response) -> None:
        status, req_id = resp.status_code, resp.headers.get("X-Request-ID")
        try: body = resp.json()
        except ValueError: body = resp.text
        m = body.get("error", {}).get("message") if isinstance(body, dict) and isinstance(body.get("error"), dict) else (body.get("message") if isinstance(body, dict) else str(body))
        k = {"status_code": status, "body": body, "request_id": req_id}
        raise (AuthError if status == 401 else APIError)(m, **k)

    def chat_completion(self, *, model: str, messages: List[dict], stream: bool = False, timeout: float = None, **kwargs: Any) -> Any:
        b = {"model": model, "messages": list(messages), "stream": stream}
        b.update(kwargs)
        return self._sse_iter("/v1/chat/completions", b, timeout=timeout) if stream else self._post_json("/v1/chat/completions", b, timeout=timeout)

    def download_storage(self, file_id: str, *, dest: str = None, timeout: float = None) -> bytes:
        meta = self._request("GET", f"/v1/storage/{file_id}", timeout=timeout).json()
        url = meta.get("signed_url") if isinstance(meta, dict) else None
        if not url: raise APIError("Missing signed_url", body=meta)
        resp = self._session.request("GET", url, timeout=timeout or self.timeout, allow_redirects=True)
        if resp.status_code >= 400: raise APIError(f"Download failed: HTTP {resp.status_code}")
        if dest: Path(os.fspath(dest)).write_bytes(resp.content)
        return resp.content

    def _sse_iter(self, path: str, body: dict, *, timeout: float = None) -> Iterator[Dict[str, Any]]:
        resp = self._request("POST", path, json=body, headers={"Accept": "text/event-stream"}, timeout=timeout, stream=True)
        try:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw or raw.startswith(":"): continue
                if raw.startswith("data:"):
                    d = raw[5:].lstrip()
                    if d == "[DONE]": return
                    try: yield json.loads(d)
                    except ValueError: yield {"_raw": d}
        finally: resp.close()
