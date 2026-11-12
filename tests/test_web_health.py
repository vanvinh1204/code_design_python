"""Kiểm thử router `GET /health` của `core_kit.web` qua `TestClient` của FastAPI."""

import importlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core_kit.web import make_health_router


def _client(version: str) -> TestClient:
    app = FastAPI()
    app.include_router(make_health_router(version))
    return TestClient(app)


def test_health_returns_200_with_status_and_version():
    response = _client("1.2.3").get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.2.3"}


def test_health_body_has_exactly_two_keys():
    body = _client("0.4.0").get("/health").json()

    assert set(body) == {"status", "version"}


def test_health_version_follows_argument():
    assert _client("9.9.9").get("/health").json()["version"] == "9.9.9"
    assert _client("0.0.1-dev").get("/health").json()["version"] == "0.0.1-dev"


def test_make_health_router_does_not_mount_itself():
    make_health_router("1.0.0")
    app = FastAPI()

    assert TestClient(app).get("/health").status_code == 404


def test_import_without_fastapi_raises_import_error_naming_extra(monkeypatch):
    """Thiếu fastapi thì import core_kit.web phải báo cài extra `core_kit[web]`; sau đó khôi phục module gốc."""
    for name in [n for n in sys.modules if n == "core_kit.web" or n.startswith("core_kit.web.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "fastapi", None)

    with pytest.raises(ImportError, match=r"core_kit\[web\]"):
        importlib.import_module("core_kit.web")

    monkeypatch.undo()
    assert importlib.import_module("core_kit.web").make_health_router is make_health_router
