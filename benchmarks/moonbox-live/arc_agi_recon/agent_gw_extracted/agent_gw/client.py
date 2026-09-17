"""Kimi agent-gw 的同步客户端。

覆盖的路由（除标注外均为 POST）：
    GET  /v1/models
    POST /v1/chat/completions       （OpenAI 兼容）
    POST /v1/messages               （Anthropic 兼容）
    POST /v1/messages/count_tokens
    POST /v1/embeddings
    POST /v1/search
    POST /v1/fetch
    POST /v1/files                  （multipart 文件上传，透传到 OpenGW）
    POST /v1/tools                  （分发器：get_stock_realtime_price、nlp_*、call_data_source_tool 等）
"""

from __future__ import annotations

import json as _json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterator, List, Mapping, Optional, Tuple, Union

import requests

from . import __version__
from .errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    PaymentRequiredError,
    QuotaExceededError,
    RateLimitError,
    ServerError,
    ToolError,
    TransportError,
)

DEFAULT_BASE_URL = "https://agent-gw-dev.dev.kimi.team/coding"
DEFAULT_TIMEOUT = 30.0
DEFAULT_USER_AGENT = f"Kimi AgentGW PySDK/{__version__}"

API_KEY_ENV_VAR = "KIMI_API_KEY"
BASE_URL_ENV_VAR = "KIMI_BASE_URL"
CHAT_ID_ENV_VAR = "KIMI_CHAT_ID"
SESSION_ID_ENV_VAR = "KIMI_SESSION_ID"
THREAD_ID_ENV_VAR = "KIMI_THREAD_ID"
EVENT_ID_ENV_VAR = "KIMI_EVENT_ID"
CONFIG_FILE = Path("~/.kimi/agent-gw.json")  # 用户家目录下的固定路径


def _load_config_file() -> Dict[str, Any]:
    """读 ``~/.kimi/agent-gw.json``，文件不存在返回 ``{}``。

    JSON 必须是 ``{"api_key": "...", "base_url": "..."}`` 形式的对象，否则抛
    ``ValueError`` —— 这是配置错误，不该静默吃掉。
    """
    path = CONFIG_FILE.expanduser()
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise ValueError(
            f"agent-gw config file {path} exists but could not be read: {e}"
        ) from e
    try:
        data = _json.loads(text)
    except _json.JSONDecodeError as e:
        raise ValueError(
            f"agent-gw config file {path} is not valid JSON: {e}"
        ) from e
    if not isinstance(data, dict):
        raise ValueError(
            f"agent-gw config file {path} must be a JSON object, got {type(data).__name__}"
        )
    return data


def _cfg_str(cfg: Mapping[str, Any], *keys: str) -> Optional[str]:
    """从 ``cfg`` 取首个非空字符串字段（自动 strip），都没值返回 ``None``。"""
    for key in keys:
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _resolve_api_key(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    """``显式参数 > KIMI_API_KEY env > JSON 配置 > 报错``"""
    if explicit:
        return explicit
    env = os.environ.get(API_KEY_ENV_VAR)
    if env and env.strip():
        return env.strip()
    file_val = _cfg_str(cfg, "api_key")
    if file_val:
        return file_val
    raise ValueError(
        "agent-gw API key not provided. Supply it via the api_key= argument, "
        f"the {API_KEY_ENV_VAR} env var, or put it in {CONFIG_FILE} as "
        '{"api_key": "sk-..."}.'
    )


def _resolve_base_url(explicit: Optional[str], cfg: Mapping[str, Any]) -> str:
    """``显式参数 > KIMI_BASE_URL env > JSON 配置 ``base_url`` > DEFAULT_BASE_URL``"""
    if explicit:
        return explicit
    env = os.environ.get(BASE_URL_ENV_VAR)
    if env and env.strip():
        return env.strip()
    file_val = _cfg_str(cfg, "base_url")
    if file_val:
        return file_val
    return DEFAULT_BASE_URL


def _resolve_kimi_chat_id(explicit: Optional[str], cfg: Mapping[str, Any]) -> Optional[str]:
    """``显式参数 > KIMI_CHAT_ID env > JSON 配置 ``kimi_chat_id`` > None``"""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get(CHAT_ID_ENV_VAR)
    if env and env.strip():
        return env.strip()
    return _cfg_str(cfg, "kimi_chat_id")


def _resolve_kimi_session_id(explicit: Optional[str], cfg: Mapping[str, Any]) -> Optional[str]:
    """``显式参数 > KIMI_SESSION_ID env > JSON 配置 ``kimi_session_id`` > None``"""
    if explicit and explicit.strip():
        return explicit.strip()
    env = os.environ.get(SESSION_ID_ENV_VAR)
    if env and env.strip():
        return env.strip()
    return _cfg_str(cfg, "kimi_session_id")


def _env_header(name: str) -> Optional[str]:
    """读取 per-exec 注入的环境变量（``KIMI_THREAD_ID`` / ``KIMI_EVENT_ID``），
    空白视为未设置。"""
    v = os.environ.get(name)
    if v and v.strip():
        return v.strip()
    return None


# 插件脚本的沙箱挂载前缀：loopy 与 darkmatter 两套布局。
PLUGIN_PATH_PREFIXES = ("/mnt/agents/plugins/", "/app/.agents/plugins/")


def _infer_plugin_name() -> Optional[str]:
    """从入口脚本路径推断插件名：``__main__.__file__`` 优先、``sys.argv[0]``
    回退；路径落在插件挂载前缀下时取前缀后的第一段目录名。"""
    candidates = []
    main_file = getattr(sys.modules.get("__main__"), "__file__", None)
    if main_file:
        candidates.append(main_file)
    if sys.argv and sys.argv[0]:
        candidates.append(sys.argv[0])
    for path in candidates:
        p = os.path.abspath(path)
        for prefix in PLUGIN_PATH_PREFIXES:
            if p.startswith(prefix):
                name = p[len(prefix):].split("/", 1)[0]
                if name:
                    return name
    return None


def _strip_tool_suffix(url: str) -> str:
    """为兼容已有 ``kimiPluginBaseUrl`` 配置，同时接受
    ``https://host`` 和 ``https://host/v1/tools`` 两种写法。"""
    url = url.rstrip("/")
    for suffix in ("/v1/tools", "/v1"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url


class ToolResponse:
    """``/v1/tools`` 返回信封的包装。

    agent-gw 返回信封结构::

        {
          "is_success": bool,
          "error": "...",
          "result": {"user": [{"text": "<内层 JSON 字符串>"}]}
        }
    """

    __slots__ = ("raw",)

    def __init__(self, raw: Any):
        # 大多数 method 返回 ``{"is_success": ..., "result": ...}`` 信封；
        # 但有的 method（如 ``get_data_source_desc``）直接返回 plain string，
        # 这里把非字典的响应包装成一个等价的成功信封，保持调用方代码一致。
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
        # 无信封字段的响应（媒体生成 / 图搜返回原始 proto JSON）：HTTP 已 200，
        # 没有显式 error 即视为成功。
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
    def text(self) -> str:
        """首条用户文本（即内层 JSON 字符串原文）。"""
        users = self.raw.get("result", {}).get("user", [])
        if users and isinstance(users[0], Mapping):
            return users[0].get("text", "") or ""
        return ""

    def json(self) -> Any:
        """把 :attr:`text` 解析为 JSON。

        - 数据源信封：返回内层 ``result.user[0].text`` 解析后的对象。
        - 媒体生成 / 图搜：响应本身就是原始 JSON（无 ``result.user`` 信封），
          直接返回整个响应体 :attr:`raw`。
        """
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


class ToolsAPI:
    """``POST /v1/tools`` 的封装。"""

    def __init__(self, client: "AgentGwClient"):
        self._client = client

    def invoke(
        self,
        method: str,
        params: Optional[Mapping[str, Any]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> ToolResponse:
        body = {"method": method, "params": dict(params or {})}
        raw = self._client._post_json("/v1/tools", body, timeout=timeout)
        return ToolResponse(raw)

    # ── Typed convenience helpers ──────────────────────────────────────────
    def stock_realtime_price(
        self,
        ticker: str,
        *,
        time: str,
        type: str = "realtime_price",
        file_path: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ToolResponse:
        """调用 ``get_stock_realtime_price``。

        参数:
            ticker:    股票代码；批量时用逗号分隔，如 ``"600519.SH"`` 或
                       ``"600519.SH,000001.SZ"``。美股需带 ``.US`` 后缀，
                       例如 ``"AAPL.US"``。
            time:      时间字符串 ``"YYYY-MM-DD HH:MM:SS"``。美股 iFind 期望
                       美东时间（ET），其余市场传北京时间。
            type:      ``"realtime_price"``（默认）或 ``"realtime_tech"``。
            file_path: 可选的 iFind 临时文件路径，例如 ``/tmp/foo.json``。
        """
        params: Dict[str, Any] = {"ticker": ticker, "time": time, "type": type}
        if file_path:
            params["file_path"] = file_path
        return self.invoke("get_stock_realtime_price", params, timeout=timeout)

    def nlp_tokenize(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_tokenize", {"text": text, **opts})

    def nlp_normalize(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_normalize", {"text": text, **opts})

    def nlp_shortkeys(self, text: str, **opts: Any) -> ToolResponse:
        return self.invoke("nlp_shortkeys", {"text": text, **opts})

    def nlp_embedding(self, texts: Union[str, List[str]], **opts: Any) -> ToolResponse:
        """调用 ``nlp_embedding``。

        服务端字段名为 ``texts``（数组），单串入参会自动包成单元素列表。
        """
        if isinstance(texts, str):
            texts = [texts]
        return self.invoke("nlp_embedding", {"texts": list(texts), **opts})

    def call_data_source_tool(self, params: Mapping[str, Any]) -> ToolResponse:
        return self.invoke("call_data_source_tool", params)

    def get_data_source_desc(self, params: Mapping[str, Any]) -> ToolResponse:
        return self.invoke("get_data_source_desc", params)

    # ── 媒体生成 / 图搜 ────────────────────────────────────────────────────
    # 这些 method 的素材与产物均为文件 URL：素材可先通过 agent-gw 的
    # ``POST /v1/storage`` 上传拿到 ``signed_url`` 再作为 reference_*_urls 传入；
    # 产物以 URL 形式在响应中返回。参数按对应 proto 字段透传，未列出的字段可用
    # ``**opts`` 传入。

    def generate_image(
        self,
        description: str,
        *,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        background: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        timeout: Optional[float] = 120.0,
        **opts: Any,
    ) -> ToolResponse:
        """调用 ``generate_image``（生图）。

        参数对应 ``agent.media.v1.GenerateImageRequest``：``ratio`` 如 ``"1:1"``，
        ``resolution`` 如 ``"1K"``，``background`` 如 ``"IMAGE_BACKGROUND_OPAQUE"``，
        ``reference_image_urls`` 为参考图的公网 URL 列表。
        """
        params: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None:
            params["ratio"] = ratio
        if resolution is not None:
            params["resolution"] = resolution
        if background is not None:
            params["background"] = background
        if reference_image_urls is not None:
            params["reference_image_urls"] = list(reference_image_urls)
        return self.invoke("generate_image", params, timeout=timeout)

    def generate_sound_effects(
        self,
        description: str,
        *,
        duration_seconds: Optional[float] = None,
        timeout: Optional[float] = 120.0,
        **opts: Any,
    ) -> ToolResponse:
        """调用 ``generate_sound_effects``（生音效音频）。"""
        params: Dict[str, Any] = {"description": description, **opts}
        if duration_seconds is not None:
            params["duration_seconds"] = duration_seconds
        return self.invoke("generate_sound_effects", params, timeout=timeout)

    def generate_speech(
        self,
        text: str,
        *,
        voice_id: Optional[str] = None,
        timeout: Optional[float] = 120.0,
        **opts: Any,
    ) -> ToolResponse:
        """调用 ``generate_speech``（生人声音频）。"""
        params: Dict[str, Any] = {"text": text, **opts}
        if voice_id is not None:
            params["voice_id"] = voice_id
        return self.invoke("generate_speech", params, timeout=timeout)

    def generate_video(
        self,
        description: str,
        *,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        reference_image_urls: Optional[List[str]] = None,
        reference_video_urls: Optional[List[str]] = None,
        reference_audio_urls: Optional[List[str]] = None,
        generate_audio: Optional[bool] = None,
        timeout: Optional[float] = 300.0,
        **opts: Any,
    ) -> ToolResponse:
        """调用 ``generate_video``（生视频）。视频生成较慢，默认 timeout 放宽到 300s。"""
        params: Dict[str, Any] = {"description": description, **opts}
        if ratio is not None:
            params["ratio"] = ratio
        if resolution is not None:
            params["resolution"] = resolution
        if duration_seconds is not None:
            params["duration_seconds"] = duration_seconds
        if reference_image_urls is not None:
            params["reference_image_urls"] = list(reference_image_urls)
        if reference_video_urls is not None:
            params["reference_video_urls"] = list(reference_video_urls)
        if reference_audio_urls is not None:
            params["reference_audio_urls"] = list(reference_audio_urls)
        if generate_audio is not None:
            params["generate_audio"] = generate_audio
        return self.invoke("generate_video", params, timeout=timeout)

    def search_image(
        self,
        keywords: Optional[Union[str, List[str]]] = None,
        *,
        page_size: Optional[int] = None,
        timeout: Optional[float] = None,
        **opts: Any,
    ) -> ToolResponse:
        """调用 ``search_image``（图搜），透传到 ``search.v3.SearchImageRequest``。

        其余字段（``scene`` / ``engines`` / ``page_token`` 等）可用 ``**opts`` 传入。
        """
        params: Dict[str, Any] = dict(opts)
        if keywords is not None:
            if isinstance(keywords, str):
                keywords = [keywords]
            params["keywords"] = list(keywords)
        if page_size is not None:
            params["page_size"] = page_size
        return self.invoke("search_image", params, timeout=timeout)


class AgentGwClient:
    """Kimi agent-gw 的同步客户端。

    ``api_key`` / ``base_url`` / ``kimi_chat_id`` 都按下面这套优先级解析（**取第一个非空**）：

        1. 此处显式传入的参数
        2. 环境变量（``KIMI_API_KEY`` / ``KIMI_BASE_URL`` / ``KIMI_CHAT_ID``）
        3. JSON 配置文件 ``~/.kimi/agent-gw.json`` 中的对应字段
        4. 兜底：``api_key`` 没有时抛 ``ValueError``；``base_url`` 退到
           ``DEFAULT_BASE_URL``；``kimi_chat_id`` 没有就不发 ``X-Kimi-Chat-Id`` 头

    JSON 文件示例::

        {
          "api_key":      "sk-...",
          "base_url":     "https://agent-gw-dev.dev.kimi.team/coding",
          "kimi_chat_id": "可选；存在则所有请求都会带 X-Kimi-Chat-Id 头",
          "kimi_session_id": "可选；存在则所有请求都会带 X-Kimi-Session-Id 头"
        }

    其它参数:
        timeout:    默认请求超时（秒）。
        skill:      可选；写入 ``X-Kimi-Skill`` 请求头。
        plugin:     可选；写入 ``X-Kimi-Plugin`` 请求头（用量归因）。不传时
                      按入口脚本路径推断：``__main__.__file__`` / ``sys.argv[0]``
                      落在 ``/mnt/agents/plugins/<name>/`` 或
                      ``/app/.agents/plugins/<name>/`` 下即自动携带 ``<name>``。
        kimi_chat_id: 可选；写入 ``X-Kimi-Chat-Id`` 请求头。不传时回落到
                      ``KIMI_CHAT_ID`` 环境变量，再不行回落到 JSON 配置文件
                      中的 ``kimi_chat_id`` 字段。
        kimi_session_id: 可选；写入 ``X-Kimi-Session-Id`` 请求头（用量归因，
                      沙箱环境由平台写进 JSON 配置的 ``kimi_session_id``
                      字段）。解析顺序同 ``kimi_chat_id``：显式参数 >
                      ``KIMI_SESSION_ID`` env > JSON 配置。

    此外每次请求会读取执行进程环境变量 ``KIMI_THREAD_ID`` / ``KIMI_EVENT_ID``
    （平台在每次沙箱 exec 时注入），存在则分别写入 ``X-Kimi-Thread-Id`` /
    ``X-Kimi-Event-Id`` 请求头，用于把 gw 调用归因回发起它的 Thread 与
    tool call。
        user_agent: 覆盖默认 User-Agent；不传时使用
                    ``"Kimi AgentGW PySDK/<version>"``。
        session:    传入自定义的 :class:`requests.Session`（连接池、
                    重试适配器、Mock 等场景）。
        extra_headers: 附加请求头，每次请求都会带上。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        skill: Optional[str] = None,
        plugin: Optional[str] = None,
        kimi_chat_id: Optional[str] = None,
        kimi_session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        session: Optional[requests.Session] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ):
        cfg = _load_config_file()
        self.api_key = _resolve_api_key(api_key, cfg)
        self.base_url = _strip_tool_suffix(_resolve_base_url(base_url, cfg))
        self.timeout = float(timeout)
        self.skill = skill
        self.plugin = (plugin.strip() if plugin and plugin.strip() else None) or _infer_plugin_name()
        self.kimi_chat_id = _resolve_kimi_chat_id(kimi_chat_id, cfg)
        self.kimi_session_id = _resolve_kimi_session_id(kimi_session_id, cfg)
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self._extra_headers = dict(extra_headers or {})
        self._session = session or requests.Session()
        self.tools = ToolsAPI(self)

    # ── lifecycle ──────────────────────────────────────────────────────────
    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "AgentGwClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ── HTTP transport ─────────────────────────────────────────────────────
    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.skill:
            h["X-Kimi-Skill"] = self.skill
        if self.plugin:
            h["X-Kimi-Plugin"] = self.plugin
        if self.kimi_chat_id:
            h["X-Kimi-Chat-Id"] = self.kimi_chat_id
        if self.kimi_session_id:
            h["X-Kimi-Session-Id"] = self.kimi_session_id
        thread_id = _env_header(THREAD_ID_ENV_VAR)
        if thread_id:
            h["X-Kimi-Thread-Id"] = thread_id
        event_id = _env_header(EVENT_ID_ENV_VAR)
        if event_id:
            h["X-Kimi-Event-Id"] = event_id
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
            # multipart: 必须让 requests 根据 files 自动生成 Content-Type 和 boundary
            h.pop("Content-Type", None)
        try:
            resp = self._session.request(
                method,
                url,
                json=json,
                data=data,
                files=files,
                params=params,
                headers=h,
                timeout=timeout if timeout is not None else self.timeout,
                stream=stream,
            )
        except requests.exceptions.Timeout as e:
            raise TransportError(f"Timeout calling {method} {path}: {e}") from e
        except requests.exceptions.RequestException as e:
            raise TransportError(f"Transport error calling {method} {path}: {e}") from e
        if resp.status_code >= 400:
            self._raise_for_status(resp)
        return resp

    def _post_json(
        self,
        path: str,
        body: Any,
        *,
        timeout: Optional[float] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        resp = self._request("POST", path, json=body, headers=headers, timeout=timeout)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _post_multipart(
        self,
        path: str,
        *,
        files: Mapping[str, Any],
        data: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        resp = self._request("POST", path, files=files, data=data, timeout=timeout)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _get_json(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        resp = self._request("GET", path, params=params, timeout=timeout)
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def _raise_for_status(self, resp: requests.Response) -> None:
        status = resp.status_code
        request_id = resp.headers.get("X-Request-ID") or resp.headers.get("x-request-id")
        body: Any
        try:
            body = resp.json()
        except ValueError:
            body = resp.text
        msg = _extract_error_message(body) or resp.reason or "request failed"
        kwargs = {"status_code": status, "body": body, "request_id": request_id}
        if status == 401:
            raise AuthenticationError(msg, **kwargs)
        if status == 402:
            raise PaymentRequiredError(msg, **kwargs)
        if status == 403:
            raise QuotaExceededError(msg, **kwargs)
        if status == 404:
            raise NotFoundError(msg, **kwargs)
        if status == 429:
            retry_after_raw = resp.headers.get("Retry-After")
            try:
                retry_after = float(retry_after_raw) if retry_after_raw else None
            except ValueError:
                retry_after = None
            raise RateLimitError(msg, retry_after=retry_after, **kwargs)
        if status >= 500:
            raise ServerError(msg, **kwargs)
        raise APIError(msg, **kwargs)

    # ── high-level endpoints ──────────────────────────────────────────────
    def list_models(self, *, timeout: Optional[float] = None) -> Any:
        return self._get_json("/v1/models", timeout=timeout)

    def chat_completion(
        self,
        *,
        model: str,
        messages: List[Mapping[str, Any]],
        stream: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        body: Dict[str, Any] = {"model": model, "messages": list(messages)}
        body.update(kwargs)
        if stream:
            body["stream"] = True
            return self._sse_iter("/v1/chat/completions", body, timeout=timeout)
        body["stream"] = False
        return self._post_json("/v1/chat/completions", body, timeout=timeout)

    def messages(
        self,
        *,
        model: str,
        messages: List[Mapping[str, Any]],
        max_tokens: int,
        stream: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        body: Dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "max_tokens": max_tokens,
        }
        body.update(kwargs)
        if stream:
            body["stream"] = True
            return self._sse_iter("/v1/messages", body, timeout=timeout)
        body["stream"] = False
        return self._post_json("/v1/messages", body, timeout=timeout)

    def count_tokens(
        self,
        *,
        model: str,
        messages: List[Mapping[str, Any]],
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        body: Dict[str, Any] = {"model": model, "messages": list(messages)}
        body.update(kwargs)
        return self._post_json("/v1/messages/count_tokens", body, timeout=timeout)

    def embeddings(
        self,
        *,
        model: str,
        input: Union[str, List[str]],
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        body: Dict[str, Any] = {"model": model, "input": input}
        body.update(kwargs)
        return self._post_json("/v1/embeddings", body, timeout=timeout)

    def search(self, query: str, *, timeout: Optional[float] = None, **kwargs: Any) -> Any:
        """调用 ``POST /v1/search``。

        参数:
            query:    搜索词；服务端字段名为 ``text_query``。
            **kwargs: 可选透传，例如 ``timeout_seconds``、``enable_page_crawling``、
                      ``limit``（详见服务端 ``websearch.Request``）。

        返回值的 ``search_results`` 字段是结果列表。
        """
        body = {"text_query": query, **kwargs}
        return self._post_json("/v1/search", body, timeout=timeout)

    def fetch(
        self,
        url: str,
        *,
        as_markdown: bool = False,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> Any:
        body = {"url": url, **kwargs}
        headers = {"Accept": "text/markdown"} if as_markdown else None
        resp = self._request("POST", "/v1/fetch", json=body, headers=headers, timeout=timeout)
        if as_markdown:
            return resp.text
        return resp.json()

    def upload_file(
        self,
        file: Union[str, "os.PathLike[str]", bytes, bytearray, BinaryIO, Tuple[Any, ...]],
        *,
        purpose: str = "file-extract",
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """调用 ``POST /v1/files`` —— multipart 文件上传，agent-gw 透传到 OpenGW。

        服务端只暴露上传（POST）一个端点，不支持 LIST/GET/DELETE/CONTENT。

        参数:
            file:         待上传的文件，支持四种写法：
                          - ``str`` 或 ``pathlib.Path``：当作文件路径，自动以二进制方式读取；
                          - ``bytes`` / ``bytearray``：原始字节，需要配合 ``filename`` 才能
                            推断扩展名（不传则用 ``"upload"``）；
                          - 类文件对象（带 ``.read()``）：调用 ``read()`` 读完整内容；
                          - ``(filename, content[, content_type])`` 元组：直接透传给 requests。
            purpose:      OpenAI 风格的 ``purpose`` 字段，agent-gw 默认值是 ``"file-extract"``。
            filename:     覆盖文件名（多 part 表单里 ``filename=`` 段）。
            content_type: 显式指定 MIME 类型；不传时按文件名后缀猜测，猜不到落到
                          ``application/octet-stream``。
            timeout:      本次请求超时（秒），不传用 client 默认。

        返回服务端 JSON 响应（含 ``id``、``object``、``filename``、``bytes`` 等字段）。
        """
        file_tuple = _build_file_tuple(file, filename=filename, content_type=content_type)
        return self._post_multipart(
            "/v1/files",
            files={"file": file_tuple},
            data={"purpose": purpose},
            timeout=timeout,
        )

    # ── 对象存储 /v1/storage（媒体素材 / 产物文件）─────────────────────────
    def upload_storage(
        self,
        file: Union[str, "os.PathLike[str]", bytes, bytearray, BinaryIO, Tuple[Any, ...]],
        *,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """调用 ``POST /v1/storage`` —— 上传素材文件，底层走 kimifs。

        与 :meth:`upload_file`（透传 OpenGW）不同：本接口返回**公网可访问的签名
        下载 URL**，可直接作为媒体生成工具（``generate_image`` / ``generate_video``
        等）的 ``reference_*_urls`` 传入。

        参数:
            file:         待上传文件，形态同 :meth:`upload_file`（路径 / 字节 /
                          类文件对象 / ``(filename, content[, content_type])`` 元组）。
            filename:     覆盖文件名。
            content_type: 显式 MIME 类型；不传按后缀猜测。
            timeout:      本次请求超时（秒）。

        返回服务端 JSON：``{file_id, file_name, size_bytes, content_type, ext,
        checksum, create_time, signed_url}``。
        """
        file_tuple = _build_file_tuple(file, filename=filename, content_type=content_type)
        return self._post_multipart(
            "/v1/storage",
            files={"file": file_tuple},
            timeout=timeout,
        )

    def get_storage_file(self, file_id: str, *, timeout: Optional[float] = None) -> Any:
        """调用 ``GET /v1/storage/{file_id}`` —— 取文件元信息并重新签发 ``signed_url``。

        返回服务端 JSON（字段同 :meth:`upload_storage`）。``file_id`` 不存在时抛
        :class:`NotFoundError`。
        """
        return self._get_json(f"/v1/storage/{file_id}", timeout=timeout)

    def download_storage(
        self,
        file_id: str,
        *,
        dest: Optional[Union[str, "os.PathLike[str]"]] = None,
        timeout: Optional[float] = None,
    ) -> bytes:
        """下载 ``/v1/storage`` 文件的二进制内容。

        先经 :meth:`get_storage_file` 拿到 ``signed_url``，再直接 ``GET`` 该 URL
        （公网，kimifs 会 307 重定向到对象存储）。agent-gw 不承载文件流量，故下载
        不带 apikey、不经网关。

        参数:
            dest:    可选；给定则把内容写入该路径。
            timeout: 本次请求超时（秒）。

        返回文件内容 ``bytes``（若 ``dest`` 给定则同时落盘）。
        """
        meta = self.get_storage_file(file_id, timeout=timeout)
        signed_url = (meta or {}).get("signed_url") if isinstance(meta, Mapping) else None
        if not signed_url:
            raise APIError("storage file has no signed_url", status_code=0, body=meta)
        try:
            # 直接打 signed_url（公网，不经网关、不带 apikey）。用 session.request
            # 而非 self._request，避免附加 Authorization 等网关头。
            resp = self._session.request(
                "GET",
                signed_url,
                timeout=timeout if timeout is not None else self.timeout,
                allow_redirects=True,
            )
        except requests.exceptions.RequestException as e:
            raise TransportError(f"download error for {file_id}: {e}") from e
        if resp.status_code >= 400:
            raise APIError(
                f"download failed: HTTP {resp.status_code}",
                status_code=resp.status_code,
                body=resp.text,
            )
        content = resp.content
        if dest is not None:
            Path(os.fspath(dest)).write_bytes(content)
        return content

    # ── server-sent events (chat/completions, messages) ───────────────────
    def _sse_iter(
        self,
        path: str,
        body: Mapping[str, Any],
        *,
        timeout: Optional[float] = None,
    ) -> Iterator[Dict[str, Any]]:
        headers = {"Accept": "text/event-stream"}
        resp = self._request(
            "POST", path, json=body, headers=headers, timeout=timeout, stream=True
        )
        try:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith(":"):  # SSE comment
                    continue
                if raw.startswith("data:"):
                    data = raw[5:].lstrip()
                    if data == "[DONE]":
                        return
                    try:
                        yield _json.loads(data)
                    except ValueError:
                        yield {"_raw": data}
        finally:
            resp.close()


def _build_file_tuple(
    file: Any,
    *,
    filename: Optional[str],
    content_type: Optional[str],
) -> Tuple[str, bytes, str]:
    """把多种文件入参形态统一成 ``(filename, content_bytes, content_type)`` 三元组，
    供 requests ``files={"file": ...}`` 使用。"""
    # 已经是 requests 接受的 tuple：原样透传（不再二次推断）
    if isinstance(file, tuple):
        return file  # type: ignore[return-value]

    def _ct(name: str) -> str:
        return content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"

    # 路径
    if isinstance(file, (str, os.PathLike)):
        path = Path(os.fspath(file))
        name = filename or path.name
        return (name, path.read_bytes(), _ct(name))

    # 原始字节
    if isinstance(file, (bytes, bytearray)):
        name = filename or "upload"
        return (name, bytes(file), _ct(name))

    # 类文件对象
    if hasattr(file, "read"):
        raw_name = filename or getattr(file, "name", None) or "upload"
        name = os.path.basename(str(raw_name))
        content = file.read()
        if isinstance(content, str):
            content = content.encode()
        return (name, content, _ct(name))

    raise TypeError(f"unsupported file type for upload: {type(file).__name__}")


def _extract_error_message(body: Any) -> Optional[str]:
    if not isinstance(body, Mapping):
        return None
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
