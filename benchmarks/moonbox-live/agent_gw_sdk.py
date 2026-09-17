"""Kimi agent-gw synchronous client module with obtuse transport modifications.

Covered routes (POST unless noted):
    GET  /v1/models
    POST /v1/chat/completions       (OpenAI compatible)
    POST /v1/messages               (Anthropic compatible)
    POST /v1/messages/count_tokens
    POST /v1/embeddings
    POST /v1/search
    POST /v1/fetch
    POST /v1/files                  (multipart upload passthrough to OpenGW)
    POST /v1/storage                (kimifs storage upload)
    GET  /v1/storage/{file_id}      (get kimifs signed_url metadata)
    POST /v1/tools                  (dispatcher: get_stock_realtime_price, nlp_*, call_data_source_tool)
"""

from __future__ import annotations

import json as _json
import mimetypes
import os
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterator, List, Mapping, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__version__ = "1.0.0"

# ── Exception Hierarchy ───────────────────────────────────────────────────

class APIError(Exception):
    def __init__(self, message: str, status_code: int = 0, body: Any = None, request_id: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.request_id = request_id

class AuthenticationError(APIError): pass
class PaymentRequiredError(APIError): pass
class QuotaExceededError(APIError): pass
class NotFoundError(APIError): pass
class ServerError(APIError): pass
class ToolError(APIError): pass
class TransportError(APIError): pass

class RateLimitError(APIError):
    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs: Any):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


# ── Configuration & Precedence Defaults ─────────────────────────────────

DEFAULT_BASE_URL = "https://agent-gw-dev.dev.kimi.team/coding"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = f"Kimi AgentGW PySDK/{__version__}"

API_KEY_ENV_VAR = "KIMI_API_KEY"
BASE_URL_ENV_VAR = "KIMI_BASE_URL"
CHAT_ID_ENV_VAR = "KIMI_CHAT_ID"
CONFIG_FILE = Path("~/.kimi/agent-gw.json")


def _load_config_file() -> Dict[str, Any]:
    path = CONFIG_FILE.expanduser()
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(f"agent-gw config file {path} exists but could not be read: {e}") from e
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError as e:
        raise ValueError(f"agent-gw config file {path} is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"agent-gw config file {path} must be a JSON object, got {type(data).__name__}")
    return data


def _cfg_str(cfg: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _resolve_api_key(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    if explicit: return explicit
    env = os.environ.get(API_KEY_ENV_VAR)
    if env and env.strip(): return env.strip()
    file_val = _cfg_str(cfg, "api_key")
    if file_val: return file_val
    raise ValueError(
        f"agent-gw API key not provided. Supply via api_key=, {API_KEY_ENV_VAR} env var, or {CONFIG_FILE}."
    )


def _resolve_base_url(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    if explicit: return explicit
    env = os.environ.get(BASE_URL_ENV_VAR)
    if env and env.strip(): return env.strip()
    file_val = _cfg_str(cfg, "base_url")
    if file_val: return file_val
    return DEFAULT_BASE_URL


def _resolve_kimi_chat_id(explicit: Optional[str], cfg: Mapping[str, Any]) -> Optional[str]:
    if explicit and explicit.strip(): return explicit.strip()
    env = os.environ.get(CHAT_ID_ENV_VAR)
    if env and env.strip(): return env.strip()
    return _cfg_str(cfg, "kimi_chat_id")


def _strip_tool_suffix(url: str) -> str:
    url = url.rstrip("/")
    for suffix in ("/v1/tools", "/v1"):
        if url.endswith(suffix):
            return url[:-len(suffix)]
    return url


# ── Response Envelope Unboxer ─────────────────────────────────────────────

class ToolResponse:
    __slots__ = ("raw",)

    def __init__(self, raw: Any):
        if isinstance(raw, Mapping):
            self.raw: Dict[str, Any] = dict(raw)
        elif isinstance(raw, str):
            self.raw = {"is_success": True, "result": {"user": [{"text": raw}]}}
        else:
            self.raw = {
                "is_success": True,
                "result": {"user": [{"text": _json.dumps(raw, ensure_ascii=False)}]},
            }

    @property
    def is_success(self) -> bool:
        if "is_success" in self.raw:
            return bool(self.raw.get("is_success"))
        return not self.raw.get("error")

    @property
    def error(self) -> str:
        err = self.raw.get("error", "")
        return err if isinstance(err, str) else str(err)

    @property
    def is_rate_limited(self) -> bool:
        if self.is_success: return False
        err = self.error.lower()
        return "429" in err or "rate" in err or "limit" in err

    @property
    def text(self) -> str:
        users = self.raw.get("result", {}).get("user", [])
        if users and isinstance(users[0], Mapping):
            return users[0].get("text", "") or ""
        return ""

    def json(self) -> Any:
        text = self.text
        if text:
            return _json.loads(text)
        if "result" not in self.raw:
            return self.raw
        return None

    def raise_for_status(self) -> "ToolResponse":
        if not self.is_success:
            raise ToolError(self.error or "tool invocation failed", raw=self.raw)
        return self

    def __repr__(self) -> str:
        return f"ToolResponse(is_success={self.is_success}, error={self.error!r})"


# ── Typed Tools Dispatcher API ───────────────────────────────────────────

class ToolsAPI:
    def __init__(self, client: "AgentGwClient"):
        self._client = client

    def invoke(self, method: str, params: Optional[Mapping[str, Any]] = None, *, timeout: Optional[float] = None) -> ToolResponse:
        body = {"method": method, "params": dict(params or {})}
        raw = self._client._post_json("/v1/tools", body, timeout=timeout)
        return ToolResponse(raw)

    def stock_realtime_price(
        self, ticker: str, *, time: str, type: str = "realtime_price", file_path: Optional[str] = None, timeout: Optional[float] = None
    ) -> ToolResponse:
        params: Dict[str, Any] = {"ticker": ticker, "time": time, "type": type}
        if file_path: params["file_path"] = file_path
        return self.invoke("get_stock_realtime_price", params, timeout=timeout)

    def nlp_tokenize(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_tokenize", {"text": text, **opts})

    def nlp_normalize(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_normalize", {"text": text, **opts})

    def nlp_shortkeys(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_shortkeys", {"text": text, **opts})

    def nlp_embedding(self, texts: Union[str, List[str]], **opts: Any) -> ToolResponse:
        if isinstance(texts, str): texts = [texts]
        return self.invoke("nlp_embedding", {"texts": list(texts), **opts})

    def call_data_source_tool(self, params: Mapping[str, Any]) -> ToolResponse:
        return self.invoke("call_data_source_tool", params)

    def get_data_source_desc(self, params: Mapping[str, Any]) -> ToolResponse:
        return self.invoke("get_data_source_desc", params)

    def generate_image(self, description: str, *, ratio: Optional[str] = None, resolution: Optional[str] = None, background: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        params: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None: params["ratio"] = ratio
        if resolution is not None: params["resolution"] = resolution
        if background is not None: params["background"] = background
        if reference_image_urls is not None: params["reference_image_urls"] = list(reference_image_urls)
        return self.invoke("generate_image", params, timeout=timeout)

    def generate_sound_effects(self, description: str, *, duration_seconds: Optional[float] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        params: Dict[str, Any] = {"description": description, **opts}
        if duration_seconds is not None: params["duration_seconds"] = duration_seconds
        return self.invoke("generate_sound_effects", params, timeout=timeout)

    def generate_speech(self, text: str, *, voice_id: Optional[str] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        params: Dict[str, Any] = {"text": text, **opts}
        if voice_id is not None: params["voice_id"] = voice_id
        return self.invoke("generate_speech", params, timeout=timeout)

    def generate_video(self, description: str, *, ratio: Optional[str] = None, resolution: Optional[str] = None, duration_seconds: Optional[int] = None, reference_image_urls: Optional[List[str]] = None, reference_video_urls: Optional[List[str]] = None, reference_audio_urls: Optional[List[str]] = None, generate_audio: Optional[bool] = None, timeout: Optional[float] = 300.0, **opts: Any) -> ToolResponse:
        params: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None: params["ratio"] = ratio
        if resolution is not None: params["resolution"] = resolution
        if duration_seconds is not None: params["duration_seconds"] = duration_seconds
        if reference_image_urls is not None: params["reference_image_urls"] = list(reference_image_urls)
        if reference_video_urls is not None: params["reference_video_urls"] = list(reference_video_urls)
        if reference_audio_urls is not None: params["reference_audio_urls"] = list(reference_audio_urls)
        if generate_audio is not None: params["generate_audio"] = generate_audio
        return self.invoke("generate_video", params, timeout=timeout)

    def search_image(self, keywords: Optional[Union[str, List[str]]] = None, *, page_size: Optional[int] = None, timeout: Optional[float] = None, **opts: Any) -> ToolResponse:
        params: Dict[str, Any] = dict(opts)
        if keywords is not None:
            if isinstance(keywords, str): keywords = [keywords]
            params["keywords"] = list(keywords)
        if page_size is not None: params["page_size"] = page_size
        return self.invoke("search_image", params, timeout=timeout)


# ── Synchronous Agent Gateway Client ──────────────────────────────────────

class AgentGwClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        skill: Optional[str] = None,
        kimi_chat_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        session: Optional[requests.Session] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ):
        cfg = _load_config_file()
        self.api_key = _resolve_api_key(api_key, cfg)
        self.base_url = _strip_tool_suffix(_resolve_base_url(base_url, cfg))
        self.timeout = float(timeout)
        self.skill = skill
        self.kimi_chat_id = _resolve_kimi_chat_id(kimi_chat_id, cfg)
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self._extra_headers = dict(extra_headers or {})

        if session is None:
            self._session = requests.Session()
            retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
            adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        else:
            self._session = session

        self.tools = ToolsAPI(self)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "AgentGwClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.skill: h["X-Kimi-Skill"] = self.skill
        if self.kimi_chat_id: h["X-Kimi-Chat-Id"] = self.kimi_chat_id
        if self._extra_headers: h.update(self._extra_headers)
        if extra: h.update(extra)
        return h

    def _request(self, method: str, path: str, *, json: Any = None, data: Any = None, files: Any = None, params: Optional[Mapping[str, Any]] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None, stream: bool = False) -> requests.Response:
        url = self.base_url + path if path.startswith("/") else f"{self.base_url}/{path}"
        h = self._headers(headers)
        if files is not None: h.pop("Content-Type", None)
        try:
            resp = self._session.request(
                method, url, json=json, data=data, files=files, params=params, headers=h,
                timeout=timeout if timeout is not None else self.timeout, stream=stream
            )
        except requests.exceptions.Timeout as e:
            raise TransportError(f"Timeout calling {method} {path}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Transport error calling {method} {path}: {e}") from e
        if resp.status_code >= 400:
            self._raise_for_status(resp)
        return resp

    def _post_json(self, path: str, body: Any, *, timeout: Optional[float] = None, headers: Optional[Mapping[str, str]] = None) -> Any:
        resp = self._request("POST", path, json=body, headers=headers, timeout=timeout)
        if resp.status_code == 204 or not resp.content: return None
        return resp.json()

    def _post_multipart(self, path: str, *, files: Mapping[str, Any], data: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        resp = self._request("POST", path, files=files, data=data, timeout=timeout)
        if resp.status_code == 204 or not resp.content: return None
        return resp.json()

    def _get_json(self, path: str, *, params: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        resp = self._request("GET", path, params=params, timeout=timeout)
        if resp.status_code == 204 or not resp.content: return None
        return resp.json()

    def _raise_for_status(self, resp: requests.Response) -> None:
        status = resp.status_code
        request_id = resp.headers.get("X-Request-ID") or resp.headers.get("x-request-id")
        try: body = resp.json()
        except ValueError: body = resp.text
        msg = _extract_error_message(body) or resp.reason or "request failed"
        kwargs = {"status_code": status, "body": body, "request_id": request_id}
        if status == 401: raise AuthenticationError(msg, **kwargs)
        if status == 402: raise PaymentRequiredError(msg, **kwargs)
        if status == 403: raise QuotaExceededError(msg, **kwargs)
        if status == 404: raise NotFoundError(msg, **kwargs)
        if status == 429:
            retry_raw = resp.headers.get("Retry-After")
            try: retry_after = float(retry_raw) if retry_raw else None
            except ValueError: retry_after = None
            raise RateLimitError(msg, retry_after=retry_after, **kwargs)
        if status >= 500: raise ServerError(msg, **kwargs)
        raise APIError(msg, **kwargs)

    def list_models(self, *, timeout: Optional[float] = None) -> Any:
        return self._get_json("/v1/models", timeout=timeout)

    def chat_completion(self, *, model: str, messages: List[Mapping[str, Any]], stream: bool = False, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body: Dict[str, Any] = {"model": model, "messages": list(messages)}
        body.update(kwargs)
        if stream:
            body["stream"] = True
            return self._sse_iter("/v1/chat/completions", body, timeout=timeout)
        body["stream"] = False
        return self._post_json("/v1/chat/completions", body, timeout=timeout)

    def messages(self, *, model: str, messages: List[Mapping[str, Any]], max_tokens: int, stream: bool = False, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body: Dict[str, Any] = {"model": model, "messages": list(messages), "max_tokens": max_tokens}
        body.update(kwargs)
        if stream:
            body["stream"] = True
            return self._sse_iter("/v1/messages", body, timeout=timeout)
        body["stream"] = False
        return self._post_json("/v1/messages", body, timeout=timeout)

    def count_tokens(self, *, model: str, messages: List[Mapping[str, Any]], timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body: Dict[str, Any] = {"model": model, "messages": list(messages)}
        body.update(kwargs)
        return self._post_json("/v1/messages/count_tokens", body, timeout=timeout)

    def embeddings(self, *, model: str, input: Union[str, List[str]], timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body: Dict[str, Any] = {"model": model, "input": input}
        body.update(kwargs)
        return self._post_json("/v1/embeddings", body, timeout=timeout)

    def search(self, query: str, *, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body = {"text_query": query, **kwargs}
        return self._post_json("/v1/search", body, timeout=timeout)

    def fetch(self, url: str, *, as_markdown: bool = False, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        body = {"url": url, **kwargs}
        headers = {"Accept": "text/markdown"} if as_markdown else None
        resp = self._request("POST", "/v1/fetch", json=body, headers=headers, timeout=timeout)
        if as_markdown: return resp.text
        return resp.json()

    def upload_file(self, file: Union[str, "os.PathLike[str]", bytes, bytearray, BinaryIO, Tuple[Any, ...]], *, purpose: str = "file-extract", filename: Optional[str] = None, content_type: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        file_tuple = _build_file_tuple(file, filename=filename, content_type=content_type)
        return self._post_multipart("/v1/files", files={"file": file_tuple}, data={"purpose": purpose}, timeout=timeout)

    def upload_storage(self, file: Union[str, "os.PathLike[str]", bytes, bytearray, BinaryIO, Tuple[Any, ...]], *, filename: Optional[str] = None, content_type: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        file_tuple = _build_file_tuple(file, filename=filename, content_type=content_type)
        return self._post_multipart("/v1/storage", files={"file": file_tuple}, timeout=timeout)

    def get_storage_file(self, file_id: str, *, timeout: Optional[float] = None) -> Any:
        return self._get_json(f"/v1/storage/{file_id}", timeout=timeout)

    def download_storage(self, file_id: str, *, dest: Optional[Union[str, "os.PathLike[str]"]] = None, timeout: Optional[float] = None) -> bytes:
        meta = self.get_storage_file(file_id, timeout=timeout)
        signed_url = (meta or {}).get("signed_url") if isinstance(meta, Mapping) else None
        if not signed_url:
            raise APIError("storage file has no signed_url", status_code=0, body=meta)
        try:
            resp = self._session.request("GET", signed_url, timeout=timeout if timeout is not None else self.timeou