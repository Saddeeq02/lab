# shared/config/user_table_templates_store.py
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
    return base / "user_table_templates.json"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class UserTableTemplate:
    id: str
    name: str              # e.g., "Widal Test"
    test_name: str         # search key; e.g., "WIDAL"
    created_at: str
    updated_at: str
    grid: dict[str, Any]   # {"rows": int, "cols": int, "cells": [[...]]}


class UserTableTemplateStore:
    @staticmethod
    def load_all() -> list[UserTableTemplate]:
        p = _store_path()
        if not p.exists():
            return []
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            out: list[UserTableTemplate] = []
            for item in raw if isinstance(raw, list) else []:
                out.append(UserTableTemplate(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    test_name=str(item.get("test_name", "")),
                    created_at=str(item.get("created_at", "")),
                    updated_at=str(item.get("updated_at", "")),
                    grid=dict(item.get("grid", {})),
                ))
            out.sort(key=lambda t: t.updated_at or t.created_at, reverse=True)
            return out
        except Exception:
            return []

    @staticmethod
    def save_all(items: list[UserTableTemplate]) -> None:
        p = _store_path()
        payload = [asdict(x) for x in items]
        p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def create(name: str, test_name: str, grid: dict[str, Any]) -> UserTableTemplate:
        tid = str(uuid.uuid4())
        now = _now()
        return UserTableTemplate(
            id=tid,
            name=name.strip(),
            test_name=test_name.strip(),
            created_at=now,
            updated_at=now,
            grid=grid,
        )

    @staticmethod
    def upsert(tpl: UserTableTemplate) -> None:
        items = UserTableTemplateStore.load_all()
        for i, x in enumerate(items):
            if x.id == tpl.id:
                tpl.updated_at = _now()
                items[i] = tpl
                UserTableTemplateStore.save_all(items)
                return
        tpl.updated_at = _now()
        items.insert(0, tpl)
        UserTableTemplateStore.save_all(items)

    @staticmethod
    def search(query: str) -> list[UserTableTemplate]:
        q = (query or "").strip().lower()
        items = UserTableTemplateStore.load_all()
        if not q:
            return items
        return [
            t for t in items
            if q in (t.name or "").lower() or q in (t.test_name or "").lower()
        ]
