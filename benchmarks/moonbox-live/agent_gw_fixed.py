"""FIXED Kimi AgentGW Client — patches ToolResponse plain-string bug."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__version__ = "1.0.0-fixed"

# ── Exception Hierarchy ───────────────────────────────────────────────────
class APIError(Exception):
    def __init__(self, msg: str, status_code: int = 0, body: Any = None, request_id: str = None):
        super().__init__(msg)
        self.status_code, self.body, self.request_id = status_code, body, request_id

class AuthError(APIError): pass
class TransportError(APIError): pass
class QuotaError(APIError): pass
class StorageFullError(APIError): pass

# ── Configuration ─────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "https://agent-gw-dev.dev.kimi.team/coding"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = f"Kimi AgentGW PySDK/{__version__}"

API_KEY_ENV_VAR = "KIMI_API_KEY"
BASE_URL_ENV_VAR = "KIMI_BASE_URL"
CONFIG_FILE = Path("~/.kimi/agent-gw.json")

# Regex to detect error-like plain strings
_ERROR_PATTERNS = re.compile(
    r"(storage\s+(full|quota|exceeded)|quota\s+exceeded|disk\s+full|"
    r"rate\s+limit|too\s+many\s+requests|unauthorized|forbidden|"
    r"payment\s+required|resource\s+exhausted)",
    re.IGNORECASE
)

# ── Config Loaders ────────────────────────────────────────────────────────
def _load_config_file() -> Dict[str, Any]:
    path = CONFIG_FILE.expanduser()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return {}

def _resolve_api_key(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    if explicit:
        return explicit
    env = os.environ.get(API_KEY_ENV_VAR)
    if env and env.strip():
        return env.strip()
    val = cfg.get("api_key")
    if isinstance(val, str) and val.strip():
        return val.strip()
    raise ValueError(f"API key not found. Set {API_KEY_ENV_VAR} or use api_key=.")

def _resolve_base_url(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    if explicit:
        return explicit
    env = os.environ.get(BASE_URL_ENV_VAR)
    if env and env.strip():
        return env.strip()
    val = cfg.get("base_url")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return DEFAULT_BASE_URL

def _strip_tool_suffix(url: str) -> str:
    url = url.rstrip("/")
    for suffix in ("/v1/tools", "/v1"):
        if url.endswith(suffix):
            return url[:-len(suffix)]
    return url

# ── FIXED ToolResponse ────────────────────────────────────────────────────
class ToolResponse:
    """Response envelope that does NOT mask plain-string errors as success."""
    __slots__ = ("raw", "_is_error_string")

    def __init__(self, raw: Any):
        self._is_error_string = False
        if isinstance(raw, Mapping):
            self.raw: Dict[str, Any] = dict(raw)
        elif isinstance(raw, str):
            # FIX: Detect error strings instead of wrapping as success
            if _ERROR_PATTERNS.search(raw):
                self._is_error_string = True
                self.raw = {
                    "is_success": False,
                    "error": raw,
                    "_detected_as": "plain_string_error"
                }
            else:
                self.raw = {"is_success": True, "result": {"user": [{"text": raw}]}}
        else:
            self.raw = {
                "is_success": True,
                "result": {"user": [{"text": json.dumps(raw, ensure_ascii=False)}]},
            }

    @property
    def is_success(self) -> bool:
        if self._is_error_string:
            return False
        if "is_success" in self.raw:
            return bool(self.raw.get("is_success"))
        return not self.raw.get("error")

    @property
    def error(self) -> str:
        err = self.raw.get("error", "")
        return err if isinstance(err, str) else str(err)

    @property
    def is_rate_limited(self) -> bool:
        if self.is_success:
            return False
        err = self.error.lower()
        return "429" in err or "rate" in err or "limit" in err

    @property
    def is_storage_full(self) -> bool:
        if self.is_success:
            return False
        err = self.error.lower()
        return "storage" in err and ("full" in err or "quota" in err or "exceeded" in err)

    @property
    def text(self) -> str:
        users = self.raw.get("result", {}).get("user", [])
        if users and isinstance(users[0], Mapping):
            return users[0].get("text", "") or ""
        return ""

    def json(self) -> Any:
        text = self.text
        if text:
            return json.loads(text)
        if "result" not in self.raw:
            return self.raw
        return None

    def raise_for_status(self) -> "ToolResponse":
        if not self.is_success:
            err = self.error or "tool invocation failed"
            if self.is_storage_full:
                raise StorageFullError(err, body=self.raw)
            if self.is_rate_limited:
                raise QuotaError(err, body=self.raw)
            raise APIError(err, body=self.raw)
        return self

    def __repr__(self) -> str:
        return f"ToolResponse(is_success={self.is_success}, error={self.error!r})"


# ── Tools Dispatcher ───────────────────────────────────────────────────────
class ToolsAPI:
    def __init__(self, client: "AgentGwClient"):
        self._client = client

    def invoke(self, method: str, params: Optional[Mapping[str, Any]] = None, *, timeout: Optional[float] = None) -> ToolResponse:
        body = {"method": method, "params": dict(params or {})}
        raw = self._client._post_json("/v1/tools", body, timeout=timeout)
        return ToolResponse(raw)

    def stock_realtime_price(self, ticker: str, *, time: str, type: str = "realtime_price", file_path: str = None, timeout: Optional[float] = None) -> ToolResponse:
        p: Dict[str, Any] = {"ticker": ticker, "time": time, "type": type}
        if file_path:
            p["file_path"] = file_path
        return self.invoke("get_stock_realtime_price", p, timeout=timeout)

    def generate_image(self, description: str, *, ratio: Optional[str] = None, resolution: Optional[str] = None, background: Optional[str] = None, reference_image_urls: Optional[List[str]] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        p: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None:
            p["ratio"] = ratio
        if resolution is not None:
            p["resolution"] = resolution
        if background is not None:
            p["background"] = background
        if reference_image_urls is not None:
            p["reference_image_urls"] = list(reference_image_urls)
        return self.invoke("generate_image", p, timeout=timeout)

    def generate_video(self, description: str, *, ratio: Optional[str] = None, resolution: Optional[str] = None, duration_seconds: Optional[int] = None, reference_image_urls: Optional[List[str]] = None, timeout: Optional[float] = 300.0, **opts: Any) -> ToolResponse:
        p: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None:
            p["ratio"] = ratio
        if resolution is not None:
            p["resolution"] = resolution
        if duration_seconds is not None:
            p["duration_seconds"] = duration_seconds
        if reference_image_urls is not None:
            p["reference_image_urls"] = list(reference_image_urls)
        return self.invoke("generate_video", p, timeout=timeout)

    def generate_sound_effects(self, description: str, *, duration_seconds: Optional[float] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        p: Dict[str, Any] = {"description": description, **opts}
        if duration_seconds is not None:
            p["duration_seconds"] = duration_seconds
        return self.invoke("generate_sound_effects", p, timeout=timeout)

    def generate_speech(self, text: str, *, voice_id: Optional[str] = None, timeout: Optional[float] = 120.0, **opts: Any) -> ToolResponse:
        p: Dict[str, Any] = {"text": text, **opts}
        if voice_id is not None:
            p["voice_id"] = voice_id
        return self.invoke("generate_speech", p, timeout=timeout)

    def search_image(self, keywords: Optional[Union[str, List[str]]] = None, *, page_size: Optional[int] = None, timeout: Optional[float] = None, **opts: Any) -> ToolResponse:
        p: Dict[str, Any] = dict(opts)
        if keywords is not None:
            if isinstance(keywords, str):
                keywords = [keywords]
            p["keywords"] = list(keywords)
        if page_size is not None:
            p["page_size"] = page_size
        return self.invoke("search_image", p, timeout=timeout)


# ── Client ────────────────────────────────────────────────────────────────
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
        self.kimi_chat_id = kimi_chat_id
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
        if self.skill:
            h["X-Kimi-Skill"] = self.skill
        if self.kimi_chat_id:
            h["X-Kimi-Chat-Id"] = self.kimi_chat_id
        if self._extra_headers:
            h.update(self._extra_headers)
        if extra:
            h.update(extra)
        return h

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        stream: bool = False,
    ) -> requests.Response:
        url = self.base_url + path if path.startswith("/") else f"{self.base_url}/{path}"
        h = self._headers(headers)
        if files is not None:
            h.pop("Content-Type", None)
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
        if resp.status_code == 204 or not resp.content:
            return None
        # FIX: Check content-type before blindly parsing JSON
        ct = resp.headers.get("Content-Type", "").lower()
        if "json" not in ct:
            # Backend returned plain text error — return as string for ToolResponse to detect
            return resp.text
        return resp.json()

    def _raise_for_status(self, resp: requests.Response) -> None:
        status = resp.status_code
        request_id = resp.headers.get("X-Request-ID") or resp.headers.get("x-request-id")
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        msg = self._extract_error_message(body) or resp.reason or "request failed"
        kwargs = {"status_code": status, "body": body, "request_id": request_id}
        if status == 401:
            raise AuthError(msg, **kwargs)
        if status == 429:
            raise QuotaError(msg, **kwargs)
        raise APIError(msg, **kwargs)

    @staticmethod
    def _extract_error_message(body: Any) -> Optional[str]:
        if not isinstance(body, Mapping):
            return str(body) if body else None
        err = body.get("error")
        if isinstance(err, Mapping):
            msg = err.get("message")
            if isinstance(msg, str) and msg:
                return msg
        if isinstance(err, str) and err:
            return err
        msg = body.get("message")
        if isinstance(msg, str) and msg:
            return msg
        return None

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

    def _get_json(self, path: str, *, params: Optional[Mapping[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        resp = self._request("GET", path, params=params, timeout=timeout)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _sse_iter(self, path: str, body: Mapping[str, Any], *, timeout: Optional[float] = None) -> Iterator[Dict[str, Any]]:
        headers = {"Accept": "text/event-stream"}
        resp = self._request("POST", path, json=body, headers=headers, timeout=timeout, stream=True)
        try:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw or raw.startswith(":"):
                    continue
                if raw.startswith("data:"):
                    data = raw[5:].lstrip()
                    if data == "[DONE]":
                        return
                    try:
                        yield json.loads(data)
                    except ValueError:
                        yield {"_raw": data}
        finally:
            resp.close()

    def upload_file(self, file: Union[str, "os.PathLike[str]", bytes, bytearray], *, purpose: str = "file-extract", filename: Optional[str] = None, content_type: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        from mimetypes import guess_type
        if isinstance(file, (str, os.PathLike)):
            path = Path(os.fspath(file))
            name = filename or path.name
            data = path.read_bytes()
        elif isinstance(file, (bytes, bytearray)):
            name = filename or "upload"
            data = bytes(file)
        else:
            raise TypeError(f"unsupported file type: {type(file).__name__}")
        ct = content_type or guess_type(name)[0] or "application/octet-stream"
        files_payload = {"file": (name, data, ct)}
        resp = self._request("POST", "/v1/files", files=files_payload, data={"purpose": purpose}, timeout=timeout)
        return resp.json()

    def upload_storage(self, file: Union[str, "os.PathLike[str]", bytes, bytearray], *, filename: Optional[str] = None, content_type: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        from mimetypes import guess_type
        if isinstance(file, (str, os.PathLike)):
            path = Path(os.fspath(file))
            name = filename or path.name
            data = path.read_bytes()
        elif isinstance(file, (bytes, bytearray)):
            name = filename or "upload"
            data = bytes(file)
        else:
            raise TypeError(f"unsupported file type: {type(file).__name__}")
        ct = content_type or guess_type(name)[0] or "application/octet-stream"
        files_payload = {"file": (name, data, ct)}
        resp = self._request("POST", "/v1/storage", files=files_payload, timeout=timeout)
        return resp.json()

    def get_storage_file(self, file_id: str, *, timeout: Optional[float] = None) -> Any:
        return self._get_json(f"/v1/storage/{file_id}", timeout=timeout)

    def download_storage(self, file_id: str, *, dest: Optional[Union[str, "os.PathLike[str]"]] = None, timeout: Optional[float] = None) -> bytes:
        meta = self.get_storage_file(file_id, timeout=timeout)
        signed_url = (meta or {}).get("signed_url") if isinstance(meta, Mapping) else None
        if not signed_url:
            raise APIError("storage file has no signed_url", status_code=0, body=meta)
        try:
            resp = self._session.request("GET", signed_url, timeout=timeout or self.timeout, allow_redirects=True)
        except requests.exceptions.RequestException as e:
            raise TransportError(f"download error for {file_id}: {e}") from e
        if resp.status_code >= 400:
            raise APIError(f"download failed: HTTP {resp.status_code}", status_code=resp.status_code, body=resp.text)
        content = resp.content
        if dest is not None:
            Path(os.fspath(dest)).write_bytes(content)
        return content


# ── Quick Test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    # Test the fixed ToolResponse
    print("Testing fixed ToolResponse...")
    
    # Test 1: Plain string that looks like an error
    r1 = ToolResponse("storage quota exceeded")
    assert r1.is_success is False, "BUG: should detect storage error"
    assert r1.is_storage_full is True
    print("  [PASS] Detects 'storage quota exceeded'")
    
    # Test 2: Plain string that is NOT an error
    r2 = ToolResponse("hello world")
    assert r2.is_success is True, "BUG: should allow benign strings"
    print("  [PASS] Allows benign plain strings")
    
    # Test 3: Normal JSON success
    r3 = ToolResponse({"is_success": True, "result": {"user": [{"text": "ok"}]}})
    assert r3.is_success is True
    print("  [PASS] Normal JSON success")
    
    # Test 4: raise_for_status on storage error
    try:
        r1.raise_for_status()
        assert False, "Should have raised StorageFullError"
    except StorageFullError:
        print("  [PASS] Raises StorageFullError")
    
    print("\nAll tests passed. SDK is fixed.")
