# shared/config/user_templates_store.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _store_path() -> Path:
    base = Path.home() / ".solunex_lab_app"
    base.mkdir(parents=True, exist_ok=True)
    return base / "user_structured_templates.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class UserTemplate:
    id: str
    name: str
    code: str
    created_at: str
    updated_at: str
    type: str  # "structured"
    parameters: list[dict[str, Any]]


class UserTemplateStore:
    @staticmethod
    def load_all() -> list[UserTemplate]:
        p = _store_path()
        if not p.exists():
            return []
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            out: list[UserTemplate] = []
            for item in raw if isinstance(raw, list) else []:
                out.append(UserTemplate(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    code=str(item.get("code", "")),
                    created_at=str(item.get("created_at", "")),
                    updated_at=str(item.get("updated_at", "")),
                    type=str(item.get("type", "structured")),
                    parameters=list(item.get("parameters", [])),
                ))
            # newest first
            out.sort(key=lambda t: t.updated_at or t.created_at, reverse=True)
            return out
        except Exception:
            return []

    @staticmethod
    def save_all(items: list[UserTemplate]) -> None:
        p = _store_path()
        payload = [asdict(x) for x in items]
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def create(name: str, parameters: list[dict[str, Any]]) -> UserTemplate:
        tid = str(uuid.uuid4())
        code = f"USER_{tid[:8].upper()}"
        now = _now()
        return UserTemplate(
            id=tid,
            name=name,
            code=code,
            created_at=now,
            updated_at=now,
            type="structured",
            parameters=parameters,
        )

    @staticmethod
    def upsert(template: UserTemplate) -> None:
        items = UserTemplateStore.load_all()
        for i, t in enumerate(items):
            if t.id == template.id:
                template.updated_at = _now()
                items[i] = template
                UserTemplateStore.save_all(items)
                return
        template.updated_at = _now()
        items.insert(0, template)
        UserTemplateStore.save_all(items)

    @staticmethod
    def delete(template_id: str) -> None:
        items = [t for t in UserTemplateStore.load_all() if t.id != template_id]
        UserTemplateStore.save_all(items)
