from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


def _settings_path() -> Path:
    base = Path.home() / ".solunex_lab_app"
    base.mkdir(parents=True, exist_ok=True)
    return base / "backend_profile.json"


@dataclass
class BackendProfile:
    enabled: bool = False
    base_url: str = "https://iandelaboratory.up.railway.app"
    role: str = "labtech"        # labtech/supervisor/admin
    timeout_s: float = 6.0

    @classmethod
    def load(cls) -> "BackendProfile":
        p = _settings_path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            merged = {**asdict(cls()), **data}
            obj = cls(**merged)

            obj.base_url = (obj.base_url or "").strip() or "https://iandelaboratory.up.railway.app"
            obj.role = (obj.role or "labtech").strip().lower()
            if obj.role not in {"labtech", "supervisor", "admin"}:
                obj.role = "labtech"
            try:
                obj.timeout_s = float(obj.timeout_s)
            except Exception:
                obj.timeout_s = 20.0

            if not isinstance(obj.enabled, bool):
                obj.enabled = False

            return obj
        except Exception:
            return cls()

    def save(self) -> None:
        p = _settings_path()
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
