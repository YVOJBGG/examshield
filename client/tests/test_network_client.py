from __future__ import annotations

from typing import Any

import pytest
import requests

from app.services.network_client import ApiClientError, HttpError, NetworkClient, NetworkError


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: dict[str, Any] | None = None,
        text: str = "",
        content: bytes = b"{}",
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text
        self.content = content
        self._json_error = json_error

    def json(self) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error
        return self._payload


def test_login_sets_token_and_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NetworkClient("http://api.example.com")
    captured: dict[str, Any] = {}

    def fake_request(**kwargs: Any) -> DummyResponse:
        captured.update(kwargs)
        return DummyResponse(payload={"access_token": "jwt-token"}, content=b'{"access_token":"jwt-token"}')

    monkeypatch.setattr(client._session, "request", fake_request)

    payload = client.login("student1", "student123")

    assert payload["access_token"] == "jwt-token"
    assert client._headers()["Authorization"] == "Bearer jwt-token"
    assert captured["url"] == "http://api.example.com/auth/login"


def test_request_raises_http_error_with_backend_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NetworkClient("http://api.example.com")
    monkeypatch.setattr(
        client._session,
        "request",
        lambda **kwargs: DummyResponse(
            status_code=403,
            payload={"detail": "Student access required"},
            text="Student access required",
            content=b'{"detail":"Student access required"}',
        ),
    )

    with pytest.raises(HttpError) as exc_info:
        client.get_student_exam("123456")

    assert exc_info.value.status_code == 403
    assert exc_info.value.message == "Student access required"


def test_request_raises_network_error_when_transport_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NetworkClient("http://api.example.com")

    def fail_request(**kwargs: Any) -> DummyResponse:
        raise requests.RequestException("connection reset")

    monkeypatch.setattr(client._session, "request", fail_request)

    with pytest.raises(NetworkError):
        client.start_attempt("123456")


def test_request_raises_api_client_error_for_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    client = NetworkClient("http://api.example.com")
    monkeypatch.setattr(
        client._session,
        "request",
        lambda **kwargs: DummyResponse(
            status_code=200,
            json_error=ValueError("bad json"),
            content=b"not-json",
        ),
    )

    with pytest.raises(ApiClientError, match="invalid JSON"):
        client.get_student_exam("123456")


def test_upload_screenshot_uses_multipart_request_with_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = NetworkClient("http://api.example.com")
    client.set_token("jwt-token")
    captured: dict[str, Any] = {}

    def fake_request(**kwargs: Any) -> DummyResponse:
        captured.update(kwargs)
        return DummyResponse(payload={"id": "shot-1"}, content=b'{"id":"shot-1"}')

    monkeypatch.setattr("app.services.network_client.requests.request", fake_request)

    payload = client.upload_screenshot(
        attempt_id="attempt-1",
        filename="screen.png",
        content=b"png-bytes",
    )

    assert payload["id"] == "shot-1"
    assert captured["url"] == "http://api.example.com/screenshots/upload"
    assert captured["headers"]["Authorization"] == "Bearer jwt-token"
    assert captured["data"]["attempt_id"] == "attempt-1"
    assert captured["files"]["file"][0] == "screen.png"
