# apps/lab_app/features/results/services/template_service.py
from __future__ import annotations

from datetime import datetime


def build_context(lab: dict, patient: dict, request: dict) -> dict[str, str]:
    return {
        "LAB_NAME": str(lab.get("lab_name", "")),
        "LAB_ADDRESS": str(lab.get("address", "")),
        "LAB_PHONE": str(lab.get("phone", "")),
        "LAB_EMAIL": str(lab.get("email", "")),

        "PATIENT_NAME": str(patient.get("Name", "")),
        "PATIENT_ID": str(patient.get("Patient ID", "")),
        "SEX": str(patient.get("Sex", "")),
        "AGE": str(patient.get("Age", "")),

        "TEST_NAME": str(request.get("test_name", "")),
        "REQUEST_ID": str(request.get("request_id", "")),
        "DATE": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def render_placeholders(raw: str, ctx: dict[str, str]) -> str:
    """
    Very safe placeholder replacement: {{KEY}}
    """
    out = raw
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v)
    return out
