# shared/config/lab_profile.py
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path


def _settings_path() -> Path:
    # Local per-machine settings (simple and reliable)
    base = Path.home() / ".solunex_lab_app"
    base.mkdir(parents=True, exist_ok=True)
    return base / "lab_profile.json"


@dataclass
class LabProfile:
    lab_name: str = "I and E Laboratory"
    address: str = "Address not set"
    phone: str = ""
    email: str = ""
    logo_path: str = ""
    watermark_enabled: bool = True

    # NEW
    scientist_name: str = ""
    scientist_qualification: str = ""
    report_notes: str = ""


    @classmethod
    def load(cls) -> "LabProfile":
        p = _settings_path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return cls(**{**cls().__dict__, **data})  # safe-ish merge
        except Exception:
            return cls()

    def save(self) -> None:
        p = _settings_path()
        p.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
