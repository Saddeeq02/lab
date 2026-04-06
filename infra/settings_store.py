# apps/solunex_lab_app/infra/settings_store.py
from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QSettings


@dataclass(frozen=True)
class BackendSettings:
    enabled: bool
    base_url: str
    role: str  # labtech/supervisor/admin (Phase A uses header)


class SettingsStore:
    """
    Persisted settings using QSettings.
    """
    ORG = "Solunex Technologies"
    APP = "IandELabApp"

    KEY_ENABLED = "backend/enabled"
    KEY_BASE_URL = "backend/base_url"
    KEY_ROLE = "backend/role"

    DEFAULT_BASE_URL = "https://api.iandelaboratory.com"
    DEFAULT_ROLE = "labtech"

    def __init__(self) -> None:
        self._qs = QSettings(self.ORG, self.APP)

    def get_backend_settings(self) -> BackendSettings:
        enabled = self._qs.value(self.KEY_ENABLED, False, type=bool)
        base_url = self._qs.value(self.KEY_BASE_URL, self.DEFAULT_BASE_URL, type=str).strip()
        role = self._qs.value(self.KEY_ROLE, self.DEFAULT_ROLE, type=str).strip().lower()
        if not base_url:
            base_url = self.DEFAULT_BASE_URL
        if role not in {"labtech", "supervisor", "admin"}:
            role = self.DEFAULT_ROLE
        return BackendSettings(enabled=enabled, base_url=base_url, role=role)

    def set_backend_enabled(self, enabled: bool) -> None:
        self._qs.setValue(self.KEY_ENABLED, bool(enabled))

    def set_base_url(self, base_url: str) -> None:
        self._qs.setValue(self.KEY_BASE_URL, (base_url or "").strip())

    def set_role(self, role: str) -> None:
        self._qs.setValue(self.KEY_ROLE, (role or "").strip().lower())
