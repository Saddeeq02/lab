# infra/api_factory.py
from __future__ import annotations

from shared.config.backend_profile import BackendProfile
from ..shared.net.api_client import ApiClient, ApiConfig

_client_instance: ApiClient | None = None


def build_api_client() -> ApiClient:
    global _client_instance

    if _client_instance is not None:
        return _client_instance

    profile = BackendProfile.load()

    _client_instance = ApiClient(
        ApiConfig(
            base_url=profile.base_url,
            role=profile.role,
            timeout_s=profile.timeout_s,
        )
    )

    return _client_instance