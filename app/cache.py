"""Redis cache helper.

Provides a thin wrapper around Redis for the URL shortener.
Designed to fail open: if Redis is unavailable, all operations silently
return None / no-op so the app degrades to DB-only mode without crashing.

Cache keys:
    url:short:<short_code>   → {original_url, is_active, url_id}  TTL 60s
    url:id:<url_id>          → full url_dict payload               TTL 60s
"""

import json
import logging
import os

log = logging.getLogger(__name__)

_TTL = 60  # seconds

# Module-level singleton; created lazily on first use
_client = None


def _get() -> "redis.Redis | None":  # type: ignore[name-defined]  # noqa: F821
    global _client
    if _client is not None:
        return _client
    try:
        import redis

        r = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        r.ping()  # confirm connectivity at startup
        _client = r
        log.info("redis_connected", extra={"host": os.environ.get("REDIS_HOST", "localhost")})
        return _client
    except Exception as exc:
        log.warning("redis_unavailable", extra={"reason": str(exc)})
        return None


# ── Public helpers ─────────────────────────────────────────────────────────────


def get_by_short_code(short_code: str) -> dict | None:
    r = _get()
    if r is None:
        return None
    try:
        raw = r.get(f"url:short:{short_code}")
        return json.loads(raw) if raw else None
    except Exception as exc:
        log.debug("cache_read_error", extra={"key": f"url:short:{short_code}", "error": str(exc)})
        return None


def set_by_short_code(short_code: str, payload: dict) -> None:
    r = _get()
    if r is None:
        return
    try:
        r.setex(f"url:short:{short_code}", _TTL, json.dumps(payload))
    except Exception as exc:
        log.debug("cache_write_error", extra={"key": f"url:short:{short_code}", "error": str(exc)})


def get_by_url_id(url_id: int) -> dict | None:
    r = _get()
    if r is None:
        return None
    try:
        raw = r.get(f"url:id:{url_id}")
        return json.loads(raw) if raw else None
    except Exception as exc:
        log.debug("cache_read_error", extra={"key": f"url:id:{url_id}", "error": str(exc)})
        return None


def set_by_url_id(url_id: int, payload: dict) -> None:
    r = _get()
    if r is None:
        return
    try:
        r.setex(f"url:id:{url_id}", _TTL, json.dumps(payload))
    except Exception as exc:
        log.debug("cache_write_error", extra={"key": f"url:id:{url_id}", "error": str(exc)})


def invalidate_url(url_id: int, short_code: str) -> None:
    """Call on PUT or DELETE so stale data doesn't linger."""
    r = _get()
    if r is None:
        return
    try:
        r.delete(f"url:id:{url_id}", f"url:short:{short_code}")
    except Exception as exc:
        log.debug("cache_invalidate_error", extra={"url_id": url_id, "error": str(exc)})
