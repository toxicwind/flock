#!/usr/bin/env python3
"""Autohook — inline error recovery with registered fix handlers.

No rollback. Fix the error and retry. Max retries configurable per hook.
"""
from __future__ import annotations

import functools
import inspect
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Global fix registry
# ---------------------------------------------------------------------------
_FIXES: List[Callable] = []


def register_fix(fn: Callable) -> Callable:
    """Register an error-fix handler. Signature: fix(exc, func, args, kwargs) -> (new_args, new_kwargs) or None."""
    _FIXES.append(fn)
    return fn


def clear_fixes() -> None:
    _FIXES.clear()


def list_fixes() -> List[Callable]:
    return list(_FIXES)


# ---------------------------------------------------------------------------
# Built-in autohooks
# ---------------------------------------------------------------------------
@register_fix
def fix_rate_limit(exc, func, args, kwargs):
    """If rate-limited, sleep until reset and retry."""
    import requests
    if hasattr(exc, "response") and exc.response is not None:
        if exc.response.status_code == 403 or exc.response.status_code == 429:
            reset = exc.response.headers.get("X-RateLimit-Reset") or exc.response.headers.get("Retry-After")
            if reset:
                try:
                    wait = max(0, int(reset) - int(time.time()) + 1)
                except (ValueError, TypeError):
                    wait = int(reset) if str(reset).isdigit() else 60
                time.sleep(min(wait, 120))
                return (args, kwargs)
            time.sleep(1)
            return (args, kwargs)
    return None


@register_fix
def fix_timeout(exc, func, args, kwargs):
    """On timeout, double the timeout and retry."""
    import requests
    if isinstance(exc, requests.exceptions.Timeout):
        kw = dict(kwargs)
        kw["timeout"] = kw.get("timeout", 30.0) * 2
        return (args, kw)
    return None


@register_fix
def fix_connection_error(exc, func, args, kwargs):
    """On connection error, replace session with fresh one and retry."""
    import requests
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError)):
        new_args = list(args)
        for i, arg in enumerate(new_args):
            if hasattr(arg, "request"):  # requests.Session
                new_args[i] = _fresh_session()
                return (tuple(new_args), kwargs)
    return None


@register_fix
def fix_ssl_error(exc, func, args, kwargs):
    """On SSL error, try with verify=False on the session."""
    import requests
    import urllib3
    if isinstance(exc, (requests.exceptions.SSLError, urllib3.exceptions.SSLError)):
        new_args = list(args)
        for i, arg in enumerate(new_args):
            if hasattr(arg, "request"):
                arg.verify = False
                return (tuple(new_args), kwargs)
    return None


@register_fix
def fix_key_error(exc, func, args, kwargs):
    """On KeyError in dict access, try with default empty dict."""
    if isinstance(exc, KeyError):
        # If the function takes a 'default' kwarg, inject it
        sig = inspect.signature(func)
        if "default" in sig.parameters:
            kw = dict(kwargs)
            kw["default"] = kw.get("default", {})
            return (args, kw)
    return None


# ---------------------------------------------------------------------------
# Session factory (used by fixes)
# ---------------------------------------------------------------------------
def _fresh_session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    s = requests.Session()
    r = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504, 429])
    a = HTTPAdapter(max_retries=r, pool_connections=20, pool_maxsize=50)
    s.mount("https://", a)
    s.mount("http://", a)
    return s


# ---------------------------------------------------------------------------
# Core Autohook decorator
# ---------------------------------------------------------------------------
class Autohook:
    """Wrap a callable with inline error recovery."""

    def __init__(self, fn: Callable, max_retries: int = 3, name: str = ""):
        self.fn = fn
        self.max_retries = max_retries
        self.name = name or getattr(fn, "__name__", "<anon>")
        functools.update_wrapper(self, fn)

    def __call__(self, *args, **kwargs):
        last_exc = None
        for attempt in range(self.max_retries):
            try:
                return self.fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                fixed = False
                for fix in _FIXES:
                    try:
                        result = fix(exc, self.fn, args, kwargs)
                        if result is not None:
                            args, kwargs = result
                            fixed = True
                            break
                    except Exception:
                        continue
                if not fixed:
                    break
        # All retries exhausted — return error dict, NEVER raise
        return {
            "_autohook_error": True,
            "_func": self.name,
            "_exception": str(last_exc),
            "_traceback": traceback.format_exc(),
            "_attempts": attempt + 1,
        }

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return functools.partial(self.__call__, instance)


def autohook(max_retries: int = 3):
    """Decorator factory. Usage: @autohook() or @autohook(max_retries=5)."""
    def decorator(fn: Callable) -> Autohook:
        return Autohook(fn, max_retries=max_retries)
    return decorator


# ---------------------------------------------------------------------------
# Parallel race executor with autohook recovery on each task
# ---------------------------------------------------------------------------
def race(tasks: List[Tuple[Callable, Tuple, Dict]], max_workers: int = 16) -> List[Any]:
    """Race all tasks in parallel via ThreadPoolExecutor. Each task wrapped with autohook."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = [None] * len(tasks)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {}
        for i, (fn, args, kwargs) in enumerate(tasks):
            wrapped = Autohook(fn, max_retries=3)
            fut = ex.submit(wrapped, *args, **kwargs)
            futures[fut] = i
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                results[idx] = fut.result(timeout=120)
            except Exception as exc:
                results[idx] = {"_autohook_error": True, "_exception": str(exc), "_traceback": traceback.format_exc()}
    return results
