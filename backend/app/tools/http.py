"""One shared way for the tools to fetch things from the internet, with a short memory (cache)
so Milo doesn't ask the same website the same question again and again."""

import time
from functools import lru_cache
from threading import Lock
from typing import Any

import httpx


class LookupFailed(Exception):
    """Raised when a website couldn't be reached or answered with an error. The message is safe to show."""


@lru_cache
def get_client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(10.0),
        follow_redirects=True,
        headers={"User-Agent": "Milo-companion/0.5 (personal project)"},
    )


_cache: dict[str, tuple[float, Any]] = {}
_cache_lock = Lock()


def _cached(key: str, max_age: float):
    with _cache_lock:
        hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < max_age:
        return hit[1]
    return None


def _remember(key: str, value: Any) -> None:
    with _cache_lock:
        if len(_cache) > 500:  # keep the cache from growing forever
            _cache.clear()
        _cache[key] = (time.monotonic(), value)


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _request(method: str, url: str, what: str, **kwargs) -> httpx.Response:
    try:
        response = get_client().request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise LookupFailed(f"Couldn't reach the {what} service. Check the internet connection.") from exc
    if response.status_code in (401, 403):
        raise LookupFailed(f"The {what} service refused the request. Check its key in backend/.env.")
    if response.status_code == 429:
        raise LookupFailed(f"The {what} service's free limit has been reached for now.")
    if response.status_code >= 400:
        raise LookupFailed(f"The {what} service answered with an error ({response.status_code}).")
    return response


def get_json(url: str, what: str, params: dict | None = None, max_age: float = 0) -> Any:
    key = f"GET {url} {sorted((params or {}).items())}"
    if max_age and (hit := _cached(key, max_age)) is not None:
        return hit
    try:
        data = _request("GET", url, what, params=params).json()
    except ValueError as exc:
        raise LookupFailed(f"The {what} service sent something unexpected.") from exc
    if max_age:
        _remember(key, data)
    return data


def get_text(url: str, what: str, max_age: float = 0) -> str:
    key = f"GET {url}"
    if max_age and (hit := _cached(key, max_age)) is not None:
        return hit
    text = _request("GET", url, what).text
    if max_age:
        _remember(key, text)
    return text


def post_json(url: str, what: str, body: dict, headers: dict | None = None) -> Any:
    try:
        return _request("POST", url, what, json=body, headers=headers or {}).json()
    except ValueError as exc:
        raise LookupFailed(f"The {what} service sent something unexpected.") from exc
