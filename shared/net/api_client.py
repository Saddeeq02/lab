# shared/net/api_client.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Dict
import requests
from shared.security.session import Session


class ApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    timeout_s: float = 6.0


class ApiClient:
    def __init__(self, config: ApiConfig):
        self.config = config

    def _url(self, path: str) -> str:
        base = self.config.base_url.rstrip("/")
        p = path if path.startswith("/") else f"/{path}"
        return f"{base}{p}"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        token = Session.token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _handle_response(self, r: requests.Response, method: str, path: str) -> Any:

        if r.status_code == 401:
            Session.clear()
            raise ApiError("Unauthorized (401). Session cleared.", status_code=401)

        if r.status_code >= 400:
            try:
                payload = r.json()
            except Exception:
                payload = r.text
            raise ApiError(
                f"HTTP {r.status_code} calling {method} {path}",
                status_code=r.status_code,
                payload=payload,
            )

        try:
            return r.json()
        except Exception as e:
            raise ApiError(
                f"Invalid JSON from {method} {path}: {e}",
                status_code=r.status_code,
                payload=r.text,
            ) from e

    def get_json(self, path: str, params: Optional[dict] = None) -> Any:
        try:
            r = requests.get(
                self._url(path),
                params=params or {},
                headers=self._headers(),
                timeout=self.config.timeout_s,
                
            )
        except requests.RequestException as e:
            raise ApiError(f"Network error calling GET {path}: {e}") from e

        return self._handle_response(r, "GET", path)

    def post_json(self, path: str, body: dict) -> Any:
        try:
            r = requests.post(
                self._url(path),
                json=body,
                headers=self._headers(),
                timeout=self.config.timeout_s,
            )
        except requests.RequestException as e:
            raise ApiError(f"Network error calling POST {path}: {e}") from e

        return self._handle_response(r, "POST", path)

    def patch_json(self, path: str, body: dict) -> Any:
        try:
            r = requests.patch(
                self._url(path),
                json=body,
                headers=self._headers(),
                timeout=self.config.timeout_s,
            )
        except requests.RequestException as e:
            raise ApiError(f"Network error calling PATCH {path}: {e}") from e

        return self._handle_response(r, "PATCH", path)

    def health(self) -> dict:
        return self.get_json("/health")

    def health_db(self) -> dict:
        return self.get_json("/health/db")