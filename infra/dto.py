# apps/solunex_lab_app/infra/dto.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


def read_count(obj: dict) -> int:
    if "Count" in obj and isinstance(obj["Count"], int):
        return obj["Count"]
    if "count" in obj and isinstance(obj["count"], int):
        return obj["count"]
    return 0


def read_value_list(obj: dict) -> list:
    v = obj.get("value", [])
    return v if isinstance(v, list) else []


@dataclass(frozen=True)
class PatientDTO:
    id: int
    patient_no: str
    full_name: str
    phone: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    address: Optional[str]


def to_patient(dto: dict) -> PatientDTO:
    return PatientDTO(
        id=int(dto["id"]),
        patient_no=str(dto.get("patient_no") or ""),
        full_name=str(dto.get("full_name") or ""),
        phone=dto.get("phone"),
        date_of_birth=dto.get("date_of_birth"),
        gender=dto.get("gender"),
        address=dto.get("address"),
    )
