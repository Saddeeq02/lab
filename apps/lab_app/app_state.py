# apps/lab_app/app_state.py
from __future__ import annotations


class AppState:
    _instance: "AppState | None" = None

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.username: str | None = None
        self.role: str | None = None
        self.branch_id: int | None = None

    @classmethod
    def instance(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_authenticated(self) -> bool:
        return bool(self.access_token)

    def clear(self) -> None:
        self.access_token = None
        self.username = None
        self.role = None
        self.branch_id = None