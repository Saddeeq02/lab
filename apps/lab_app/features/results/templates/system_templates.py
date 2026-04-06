# apps/lab_app/features/results/templates/system_templates.py
from __future__ import annotations


def list_system_templates() -> list[dict]:
    """
    Phase-2: registry of structured templates.
    Later: move to DB/API + versioning.
    """
    return [
        {
            "code": "FBC",
            "name": "Full Blood Count (FBC)",
            "aliases": ["fbc", "full blood count", "full blood count (fbc)"],
            "type": "structured",
            "parameters": [
                {"name": "Hemoglobin (Hb)", "unit": "g/dL", "ref": {"male": (13.0, 17.0), "female": (12.0, 15.0)}},
                {"name": "WBC", "unit": "x10^9/L", "ref": (4.0, 11.0)},
                {"name": "Platelets", "unit": "x10^9/L", "ref": (150.0, 450.0)},
                {"name": "RBC", "unit": "x10^12/L", "ref": {"male": (4.5, 5.9), "female": (4.1, 5.1)}},
                {"name": "Hematocrit (HCT)", "unit": "%", "ref": {"male": (41.0, 53.0), "female": (36.0, 46.0)}},
            ],
        },
        {
            "code": "RBS",
            "name": "Random Blood Sugar (RBS)",
            "aliases": ["rbs", "random blood sugar", "glucose rbs"],
            "type": "structured",
            "parameters": [
                {"name": "Glucose (Random)", "unit": "mmol/L", "ref": (3.9, 7.8)},
            ],
        },
        {
            "code": "FBS",
            "name": "Fasting Blood Sugar (FBS)",
            "aliases": ["fbs", "fasting blood sugar", "glucose fbs"],
            "type": "structured",
            "parameters": [
                {"name": "Glucose (Fasting)", "unit": "mmol/L", "ref": (3.9, 5.5)},
            ],
        },
        {
            "code": "U_E",
            "name": "Urea & Electrolytes (U&E)",
            "aliases": ["u&e", "ue", "urea and electrolytes", "urea electrolytes", "electrolytes"],
            "type": "structured",
            "parameters": [
                {"name": "Sodium (Na+)", "unit": "mmol/L", "ref": (135.0, 145.0)},
                {"name": "Potassium (K+)", "unit": "mmol/L", "ref": (3.5, 5.1)},
                {"name": "Chloride (Cl-)", "unit": "mmol/L", "ref": (98.0, 107.0)},
                {"name": "Bicarbonate (HCO3-)", "unit": "mmol/L", "ref": (22.0, 29.0)},
                {"name": "Urea", "unit": "mmol/L", "ref": (2.5, 7.8)},
                {"name": "Creatinine", "unit": "µmol/L", "ref": {"male": (74.0, 110.0), "female": (58.0, 96.0)}},
            ],
        },
    ]


def match_system_template(test_name: str) -> dict | None:
    """
    Matches by aliases and substring.
    """
    name = (test_name or "").strip().lower()
    if not name:
        return None

    for t in list_system_templates():
        aliases = [a.lower() for a in t.get("aliases", [])]
        if name in aliases:
            return t
        if any(a in name for a in aliases):
            return t
        if t["code"].lower() in name:
            return t

    return None
