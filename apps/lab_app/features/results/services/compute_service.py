# apps/lab_app/features/results/services/compute_service.py
from __future__ import annotations

from typing import Any, Optional, Tuple


def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        return float(s)
    except Exception:
        return None


def _ensure_cell(values: dict, r: int, c: int) -> None:
    cells = values.setdefault("cells", [])
    while len(cells) <= r:
        cells.append([])
    while len(cells[r]) <= c:
        cells[r].append("")


def _get_cell(values: dict, r: int, c: int) -> str:
    cells = (values or {}).get("cells") or []
    if r < 0 or r >= len(cells):
        return ""
    row = cells[r] or []
    if c < 0 or c >= len(row):
        return ""
    return str(row[c] or "").strip()


def _set_cell(values: dict, r: int, c: int, text: str) -> None:
    _ensure_cell(values, r, c)
    values["cells"][r][c] = str(text)


def compute_grid_flags_and_apply(
    *,
    template_snapshot: dict,
    values: dict,
) -> Tuple[dict, dict]:
    """
    UI-side grid auto-flagging (table format) using snapshot["schema"] mapping.

    Returns:
      (updated_values, flags_dict)

    - updated_values: same shape as values, but writes computed flag string into the mapped Flag column.
    - flags_dict: structured summary for optional persistence/preview.
    """
    snap = template_snapshot or {}
    kind = str(snap.get("kind") or "").strip().lower()
    if kind != "grid":
        return (values or {}, {})

    schema = (snap.get("schema") or {})
    enabled = bool(schema.get("enabled", False))
    if not enabled:
        return (values or {}, {"kind": "grid", "enabled": False})

    header_row = int(schema.get("header_row", 0) or 0)
    cols = (schema.get("columns") or {})

    c_param = cols.get("parameter")
    c_res = cols.get("result")
    c_unit = cols.get("unit")  # optional; not used for minmax calc
    c_lo = cols.get("ref_min")
    c_hi = cols.get("ref_max")
    c_flag = cols.get("flag")

    # minimum required mapping
    if c_res is None or c_lo is None or c_hi is None or c_flag is None:
        return (values or {}, {
            "kind": "grid",
            "enabled": True,
            "error": "incomplete_schema",
            "schema": schema,
            "rows": [],
            "changed_cells": 0,
        })

    updated = values or {}
    cells = updated.get("cells") or []
    row_count = len(cells)

    # bounds sanity (avoid crashing on bad schema)
    maxc = 0
    for r in cells:
        if isinstance(r, list) and len(r) > maxc:
            maxc = len(r)
    maxc = maxc - 1

    for cc in (c_res, c_lo, c_hi, c_flag):
        try:
            if int(cc) < 0 or int(cc) > maxc:
                return (updated, {
                    "kind": "grid",
                    "enabled": True,
                    "error": "schema_out_of_range",
                    "schema": schema,
                    "rows": [],
                    "changed_cells": 0,
                })
        except Exception:
            return (updated, {
                "kind": "grid",
                "enabled": True,
                "error": "schema_invalid",
                "schema": schema,
                "rows": [],
                "changed_cells": 0,
            })

    rows_out: list[dict] = []
    changed = 0

    for r in range(header_row + 1, row_count):
        res = _to_float(_get_cell(updated, r, int(c_res)))
        lo = _to_float(_get_cell(updated, r, int(c_lo)))
        hi = _to_float(_get_cell(updated, r, int(c_hi)))

        # only compute when all numeric exist
        if res is None or lo is None or hi is None:
            continue

        flag = "NORMAL"
        if res < lo:
            flag = "LOW"
        elif res > hi:
            flag = "HIGH"

        prev = _get_cell(updated, r, int(c_flag))
        if (prev or "").strip() != flag:
            _set_cell(updated, r, int(c_flag), flag)
            changed += 1

        param_val = None
        if c_param is not None:
            try:
                param_val = _get_cell(updated, r, int(c_param)) or None
            except Exception:
                param_val = None

        unit_val = None
        if c_unit is not None:
            try:
                unit_val = _get_cell(updated, r, int(c_unit)) or None
            except Exception:
                unit_val = None

        rows_out.append({
            "row_index": r,
            "parameter": param_val,
            "unit": unit_val,
            "result": float(res),
            "ref_min": float(lo),
            "ref_max": float(hi),
            "flag": flag,
        })

    flags = {
        "kind": "grid",
        "mode": schema.get("mode") or "minmax",
        "schema": schema,
        "rows": rows_out,
        "changed_cells": changed,
    }
    return (updated, flags)
