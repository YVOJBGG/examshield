from __future__ import annotations

from typing import Any

import requests


class ApiClientError(Exception):
    pass


class NetworkError(ApiClientError):
    pass


class HttpError(ApiClientError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.message = message


class NetworkClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None
        self._session = requests.Session()
        self._timeout_seconds = 15

    def set_token(self, token: str) -> None:
        self._token = token

    def clear_token(self) -> None:
        self._token = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=self._headers(),
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise NetworkError(f"Network request failed: {exc}") from exc

        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise HttpError(response.status_code, message)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("Server returned invalid JSON") from exc

    def _multipart_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request_multipart(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any],
        files: dict[str, tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._multipart_headers(),
                data=data,
                files=files,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise NetworkError(f"Network request failed: {exc}") from exc

        if response.status_code >= 400:
            message = self._extract_error_message(response)
            raise HttpError(response.status_code, message)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ApiClientError("Server returned invalid JSON") from exc

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            body = response.json()
            detail = body.get("detail")
            if isinstance(detail, str) and detail:
                return detail
        except ValueError:
            pass
        return response.text or "Request failed"

    def login(self, username: str, password: str) -> dict[str, Any]:
        data = self._request(
            "POST",
            "/auth/login",
            {"username": username, "password": password},
        )
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise ApiClientError("Login response missing access_token")
        self.set_token(token)
        return data

    def get_student_exam(self, exam_code: str) -> dict[str, Any]:
        return self._request("GET", f"/student/exams/{exam_code}")

    def start_attempt(self, exam_code: str) -> dict[str, Any]:
        return self._request("POST", "/attempts/start", {"exam_code": exam_code})

    def autosave_answers(self, attempt_id: str, answers: list[dict[str, str]]) -> Any:
        return self._request(
            "POST",
            "/answers/autosave",
            {"attempt_id": attempt_id, "answers": answers},
        )

    def submit_answers(self, attempt_id: str, answers: list[dict[str, str]]) -> Any:
        return self._request(
            "POST",
            "/answers/submit",
            {"attempt_id": attempt_id, "answers": answers},
        )

    def send_monitoring_status(
        self,
        *,
        event_type: str,
        exam_id: str,
        attempt_id: str,
        status: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": event_type,
            "exam_id": exam_id,
            "attempt_id": attempt_id,
            "status": status,
        }
        if message:
            payload["message"] = message
        return self._request("POST", "/monitoring/status", payload)

    def report_violation(
        self,
        *,
        attempt_id: str,
        violation_type: str,
        details: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "attempt_id": attempt_id,
            "type": violation_type,
        }
        if details:
            payload["details"] = details
        return self._request("POST", "/violations", payload)

    def upload_screenshot(
        self,
        *,
        attempt_id: str,
        filename: str,
        content: bytes,
        content_type: str = "image/png",
    ) -> dict[str, Any]:
        return self._request_multipart(
            "POST",
            "/screenshots/upload",
            data={"attempt_id": attempt_id},
            files={"file": (filename, content, content_type)},
        )
