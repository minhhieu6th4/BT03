import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from backend.config.settings import settings
from backend.services.match_queue import enqueue_or_run_inline


def test_auto_mode_falls_back_inline_only_outside_production(monkeypatch):
    called = []
    monkeypatch.setattr(settings, "MATCH_EXECUTION_MODE", "auto")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")

    class UnavailableRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            return UnavailableRedis()

        @staticmethod
        def ping():
            raise ConnectionError("redis offline")

        @staticmethod
        def close():
            pass

    monkeypatch.setattr("backend.services.match_queue.Redis", UnavailableRedis)

    result = enqueue_or_run_inline(
        "backend.jobs.run_room_match",
        (1,),
        lambda: called.append(True),
    )

    assert result is None
    assert called == [True]


def test_production_queue_failure_returns_service_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "MATCH_EXECUTION_MODE", "auto")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    class UnavailableRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            return UnavailableRedis()

        @staticmethod
        def ping():
            raise ConnectionError("redis offline")

        @staticmethod
        def close():
            pass

    monkeypatch.setattr("backend.services.match_queue.Redis", UnavailableRedis)

    with pytest.raises(HTTPException) as error:
        enqueue_or_run_inline(
            "backend.jobs.run_room_match",
            (1,),
            lambda: pytest.fail("must not run inline"),
        )

    assert error.value.status_code == 503