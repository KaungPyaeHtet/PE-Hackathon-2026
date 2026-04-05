"""Redis cache layer: fail-open when Redis is down; happy path with fakeredis."""

import importlib

import fakeredis
import pytest
import redis as redis_lib


@pytest.fixture
def cache_fake(monkeypatch):
    monkeypatch.setattr(
        redis_lib,
        "Redis",
        lambda **kwargs: fakeredis.FakeRedis(decode_responses=True),
    )
    import app.cache as cache_mod

    importlib.reload(cache_mod)
    cache_mod._client = None
    yield cache_mod
    cache_mod._client = None


@pytest.fixture
def cache_down(monkeypatch):
    class RedisDown:
        def __init__(self, **kwargs):
            raise ConnectionError("redis refused")

    monkeypatch.setattr(redis_lib, "Redis", RedisDown)
    import app.cache as cache_mod

    importlib.reload(cache_mod)
    cache_mod._client = None
    yield cache_mod
    cache_mod._client = None


def test_redis_unavailable_returns_none(cache_down):
    assert cache_down.get_by_short_code("any") is None
    assert cache_down.get_by_url_id(999) is None
    cache_down.set_by_short_code("x", {"a": 1})
    cache_down.set_by_url_id(1, {"id": 1})
    cache_down.invalidate_url(1, "x")


def test_short_code_round_trip(cache_fake):
    payload = {"original_url": "https://ex.test", "is_active": True, "url_id": 42}
    cache_fake.set_by_short_code("abc", payload)
    assert cache_fake.get_by_short_code("abc") == payload


def test_url_id_round_trip(cache_fake):
    row = {"id": 7, "short_code": "zz", "original_url": "https://z"}
    cache_fake.set_by_url_id(7, row)
    assert cache_fake.get_by_url_id(7) == row


def test_corrupt_json_in_cache_returns_none(cache_fake):
    r = fakeredis.FakeRedis(decode_responses=True)
    r.set("url:short:bad", "not-valid-json{{{")
    cache_fake._client = r
    assert cache_fake.get_by_short_code("bad") is None


def test_setex_failure_swallowed(cache_fake):
    r = fakeredis.FakeRedis(decode_responses=True)

    def boom(*_a, **_k):
        raise RuntimeError("setex failed")

    r.setex = boom
    cache_fake._client = r
    cache_fake.set_by_short_code("k", {"x": 1})


def test_setex_failure_url_id_swallowed(cache_fake):
    r = fakeredis.FakeRedis(decode_responses=True)

    def boom(*_a, **_k):
        raise RuntimeError("setex failed")

    r.setex = boom
    cache_fake._client = r
    cache_fake.set_by_url_id(3, {"id": 3})


def test_invalidate_deletes_keys(cache_fake):
    cache_fake.set_by_short_code("s1", {"url_id": 9})
    cache_fake.set_by_url_id(9, {"id": 9})
    cache_fake.invalidate_url(9, "s1")
    assert cache_fake.get_by_short_code("s1") is None
    assert cache_fake.get_by_url_id(9) is None


def test_invalidate_delete_error_swallowed(cache_fake):
    r = fakeredis.FakeRedis(decode_responses=True)

    def boom(*_a, **_k):
        raise RuntimeError("delete failed")

    r.delete = boom
    cache_fake._client = r
    cache_fake.invalidate_url(1, "x")


def test_get_by_url_id_corrupt_json(cache_fake):
    r = fakeredis.FakeRedis(decode_responses=True)
    r.set("url:id:5", "{")
    cache_fake._client = r
    assert cache_fake.get_by_url_id(5) is None
