# apps/lab_app/features/results/views/result_structured_editor.py
from __future__ import annotations

from typing import Tuple, Optional, Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QDialog
)
import re
from apps.lab_app.features.results.templates.system_templates import (
    match_system_template, list_system_templates
)

from shared.config.user_templates_store import UserTemplateStore
from shared.uix.widgets.dialogs import TemplateBuilderDialog


class StructuredResultEditorView(QWidget):
    """
    Phase-1 Structured Table Editor
    - Fixed columns: Parameter | Result | Unit | Ref Range | Flag
    - Only Result column is editable
    - Live flagging: Low/Normal/High/Invalid
    - Save emits a structured payload (with template snapshot for history integrity)
    """

    saved = Signal(dict)

    COL_PARAM = 0
    COL_RESULT = 1
    COL_UNIT = 2
    COL_REF = 3
    COL_FLAG = 4

    def __init__(self, patient_row: dict, request: dict):
        super().__init__()
        self.patient_row = patient_row or {}
        self.request = request or {}

        # Templates
        self._templates = list_system_templates()
        self._user_templates = UserTemplateStore.load_all()

        self.template = match_system_template(self.request.get("test_name", ""))
        if not self.template:
            self.template = {
                "code": "GEN",
                "name": self.request.get("test_name", "Unknown Test"),
                "type": "structured",
                "parameters": [],
                "template_source": "system",
            }

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Header
        header = QLabel(self._header_text())
        header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.setStyleSheet(
            "padding: 10px; border: 1px solid #d9d9d9; border-radius: 10px; "
            "background: #fafafa; font-weight: 600;"
        )
        root.addWidget(header)

        # Controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Structured Template:"))

        self.template_picker = QComboBox()
        self._rebuild_template_picker()
        self.template_picker.currentIndexChanged.connect(self._on_template_changed)
        controls.addWidget(self.template_picker)

        controls.addStretch()

        self.btn_save_template = QPushButton("Save as Template")
        self.btn_save_template.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_template.clicked.connect(self._save_as_template)
        controls.addWidget(self.btn_save_template)

        self.btn_save = QPushButton("Submit for Release")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        controls.addWidget(self.btn_save)

        root.addLayout(controls)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Parameter", "Result", "Unit", "Ref. Range", "Flag"])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("QTableWidget { border: 1px solid #d9d9d9; border-radius: 8px; }")
        root.addWidget(self.table, 1)

        self._load_parameters()
        self.table.itemChanged.connect(self._on_item_changed)

    # -------------------------
    # Helpers
    # -------------------------
    def _header_text(self) -> str:
        pid = self.patient_row.get("Patient ID", "-")
        name = self.patient_row.get("Name", "-")
        sex = str(self.patient_row.get("Sex", "-")).strip().lower()
        age = self.patient_row.get("Age", "-")
        test = self.request.get("test_name", "Unknown Test")
        rid = self.request.get("request_id", "-")
        return f"Patient: {name} | {pid} | {sex.upper()} | {age}\nTest: {test} | Request ID: {rid}"

    def _patient_sex_key(self) -> str:
        sex = str(self.patient_row.get("Sex", "")).strip().lower()
        if sex in ("m", "male"):
            return "male"
        if sex in ("f", "female"):
            return "female"
        return "all"

    def _resolve_ref(self, ref: Any) -> Tuple[Optional[float], Optional[float], str]:
        """
        Returns (min, max, display_text)
        ref can be:
          - (min, max)
          - {"male": (min,max), "female": (min,max)}
        """
        if isinstance(ref, dict):
            sex_key = self._patient_sex_key()
            if sex_key in ref:
                lo, hi = ref[sex_key]
                return float(lo), float(hi), f"{lo} - {hi}"
            # fallback
            if "male" in ref:
                lo, hi = ref["male"]
                return float(lo), float(hi), f"{lo} - {hi}"
            if "female" in ref:
                lo, hi = ref["female"]
                return float(lo), float(hi), f"{lo} - {hi}"
            return None, None, "—"
        if isinstance(ref, (tuple, list)) and len(ref) == 2:
            lo, hi = ref
            return float(lo), float(hi), f"{lo} - {hi}"
        return None, None, "—"

    # -------------------------
    # Template Picker
    # -------------------------
    def _rebuild_template_picker(self) -> None:
        self._user_templates = UserTemplateStore.load_all()

        self.template_picker.blockSignals(True)
        self.template_picker.clear()

        self.template_picker.addItem("Auto (based on test name)", ("auto", None))

        for t in self._templates:
            self.template_picker.addItem(f"[System] {t['name']}", ("system", t["code"]))

        for u in self._user_templates:
            self.template_picker.addItem(f"[My] {u.name}", ("user", u.id))

        self.template_picker.blockSignals(False)

        # Default selection to Auto
        self.template_picker.setCurrentIndex(0)

    def _on_template_changed(self, idx: int) -> None:
        data = self.template_picker.currentData()
        if not data:
            return

        kind, key = data

        if kind == "auto":
            # Override logic: if a user template name matches the test name exactly, prefer it.
            test_name = (self.request.get("test_name", "") or "").strip().lower()
            self._user_templates = UserTemplateStore.load_all()
            user_match = next((u for u in self._user_templates if (u.name or "").strip().lower() == test_name), None)

            if user_match:
                self.template = {
                    "code": user_match.code,
                    "name": user_match.name,
                    "type": "structured",
                    "parameters": user_match.parameters,
                    "template_source": "user",
                    "template_id": user_match.id,
                }
            else:
                self.template = match_system_template(self.request.get("test_name", "")) or self.template

        elif kind == "system":
            for t in self._templates:
                if t.get("code") == key:
                    self.template = t
                    self.template.setdefault("template_source", "system")
                    break

        elif kind == "user":
            self._user_templates = UserTemplateStore.load_all()
            found = next((t for t in self._user_templates if t.id == key), None)
            if found:
                self.template = {
                    "code": found.code,
                    "name": found.name,
                    "type": "structured",
                    "parameters": found.parameters,
                    "template_source": "user",
                    "template_id": found.id,
                }

        # Re-render parameters and reset results for safety
        self.table.blockSignals(True)
        self._load_parameters()
        self.table.blockSignals(False)

        for r in range(self.table.rowCount()):
            result_item = self.table.item(r, self.COL_RESULT)
            flag_item = self.table.item(r, self.COL_FLAG)
            if result_item:
                result_item.setText("")
            if flag_item:
                flag_item.setText("—")

    # -------------------------
    # Table load / flagging
    # -------------------------
    def _load_parameters(self) -> None:
        params = self.template.get("parameters", []) or []
        self.table.setRowCount(len(params))

        for r, p in enumerate(params):
            pname = p.get("name", "")
            unit = p.get("unit", "")
            lo, hi, ref_text = self._resolve_ref(p.get("ref"))

            it_name = QTableWidgetItem(str(pname))
            it_name.setFlags(it_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, self.COL_PARAM, it_name)

            it_res = QTableWidgetItem("")
            it_res.setFlags(it_res.flags() | Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, self.COL_RESULT, it_res)

            it_unit = QTableWidgetItem(str(unit))
            it_unit.setFlags(it_unit.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, self.COL_UNIT, it_unit)

            it_ref = QTableWidgetItem(ref_text)
            it_ref.setFlags(it_ref.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, self.COL_REF, it_ref)

            it_flag = QTableWidgetItem("—")
            it_flag.setFlags(it_flag.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(r, self.COL_FLAG, it_flag)

        self.table.resizeColumnsToContents()

    def _on_item_changed(self, item: QTableWidgetItem | None) -> None:
        if not item or item.column() != self.COL_RESULT:
            return

        row = item.row()
        if not isinstance(self.template, dict):
            return
        params = self.template.get("parameters", []) or []
        if row < 0 or row >= len(params):
            return

        lo, hi, _ = self._resolve_ref(params[row].get("ref"))
        flag_item = self.table.item(row, self.COL_FLAG)

        text = (item.text() or "").strip()
        if not text:
            if flag_item:
                flag_item.setText("—")
            return

        try:
            val = float(text)
        except ValueError:
            if flag_item:
                flag_item.setText("Invalid")
            return

        if lo is None or hi is None:
            if flag_item:
                flag_item.setText("—")
            return

        if flag_item:
            if val < lo:
                flag_item.setText("Low")
            elif val > hi:
                flag_item.setText("High")
            else:
                flag_item.setText("Normal")

    # -------------------------
    # Payload helpers
    # -------------------------
    def _extract_rows(self) -> list[dict]:
        out: list[dict] = []
        if not isinstance(self.template, dict):
            return out
        params = self.template.get("parameters", []) or []

        for r in range(self.table.rowCount()):
            param_item = self.table.item(r, self.COL_PARAM)
            result_item = self.table.item(r, self.COL_RESULT)
            unit_item = self.table.item(r, self.COL_UNIT)
            ref_item = self.table.item(r, self.COL_REF)
            flag_item = self.table.item(r, self.COL_FLAG)

            name = param_item.text() if param_item else ""
            result = (result_item.text() if result_item else "").strip()
            unit = unit_item.text() if unit_item else ""
            ref = ref_item.text() if ref_item else ""
            flag = flag_item.text() if flag_item else ""

            ref_raw = params[r].get("ref") if r < len(params) else None

            out.append({
                "parameter": name,
                "result": result,
                "unit": unit,
                "ref_range": ref,
                "ref_raw": ref_raw,
                "flag": flag,
            })
        return out

    def load_payload(self, payload: dict) -> None:
        rows = payload.get("rows", [])
        if not rows:
            return

        lookup = {r.get("parameter"): str(r.get("result", "")).strip() for r in rows}

        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            param_item = self.table.item(r, self.COL_PARAM)
            result_item = self.table.item(r, self.COL_RESULT)
            if param_item and result_item:
                pname = param_item.text()
                val = lookup.get(pname, "")
                result_item.setText(val)
        self.table.blockSignals(False)

        for r in range(self.table.rowCount()):
            self._on_item_changed(self.table.item(r, self.COL_RESULT))

    # -------------------------
    # Save as Template
    # -------------------------
    def _save_as_template(self) -> None:
        params: list[dict] = []

        if not isinstance(self.template, dict):
            return
        tparams = self.template.get("parameters", []) or []
        for r in range(self.table.rowCount()):
            param_item = self.table.item(r, self.COL_PARAM)
            unit_item = self.table.item(r, self.COL_UNIT)
            pname = param_item.text() if param_item else ""
            unit = unit_item.text() if unit_item else ""
            pname = pname.strip()
            unit = unit.strip()

            if not pname:
                continue

            ref_raw = (0.0, 0.0)
            if r < len(tparams):
                ref = tparams[r].get("ref")
                if isinstance(ref, (tuple, list)) and len(ref) == 2:
                    try:
                        ref_raw = (float(ref[0]), float(ref[1]))
                    except Exception:
                        ref_raw = (0.0, 0.0)

            params.append({"name": pname, "unit": unit, "ref": ref_raw})

        dlg = TemplateBuilderDialog(self, name="", parameters=params)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.is_saved():
            return

        name = dlg.template_name()
        parameters = dlg.parameters()

        ut = UserTemplateStore.create(name=name, parameters=parameters)
        UserTemplateStore.upsert(ut)

        # Rebuild picker and select new template
        self._rebuild_template_picker()

        for i in range(self.template_picker.count()):
            data = self.template_picker.itemData(i)
            if data and data[0] == "user" and data[1] == ut.id:
                self.template_picker.setCurrentIndex(i)
                break

    # -------------------------
    # Save Result
    # -------------------------
    def _save(self) -> None:
        rows = self._extract_rows()

        any_value = any((row.get("result") or "").strip() for row in rows)
        if not any_value:
            QMessageBox.information(self, "Nothing to save", "Please enter at least one result value before saving.")
            return

        if not isinstance(self.template, dict):
            QMessageBox.warning(self, "Error", "Invalid template configuration.")
            return

        template_snapshot, values = self._build_uix_snapshot_and_values(rows)

        payload = {
            "type": "structured",
            "patient": dict(self.patient_row),
            "request": dict(self.request),

            # UIX-first backend payload pieces (authoritative)
            "uix": {
                "test_type_id": self.request.get("test_type_id"),  # ensure caller provides this
                "template_id": None,  # UIX-first: provenance optional; set if you want
                "template_snapshot": template_snapshot,
                "values": values,
            },

            # Keep the old rows for local history / display if you still want it
            "rows": rows,

            # Optional metadata
            "status": "pending_release",
            "notes": "",  # your UI can add notes later
        }

        # Replace noisy print with one clear diagnostic
        print(f"UIX_SAVE snapshot_fields={len(template_snapshot.get('fields', []))} values_keys={list(values.keys())}")

        self.saved.emit(payload)
        QMessageBox.information(self, "Submitted", "Result submitted to the Hub. Waiting for Cashier to release.")

    def _slug_key(self, name: str) -> str:
        # Deterministic key generator for backend values dict
        s = (name or "").strip().lower()

        # Common aliases (extend as needed)
        aliases = {
            "hemoglobin (hb)": "hb",
            "hemoglobin": "hb",
            "hb": "hb",
            "white blood cells": "wbc",
            "wbc": "wbc",
            "platelets": "platelets",
            "plt": "platelets",
            "red blood cells": "rbc",
            "rbc": "rbc",
            "hematocrit (hct)": "hct",
            "hematocrit": "hct",
            "hct": "hct",
            "pcv": "hct",
        }
        if s in aliases:
            return aliases[s]

        # Remove parentheses content but keep abbreviations if present
        s = re.sub(r"\s*\([^)]*\)\s*", " ", s).strip()

        # Slugify
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s or "field"

    def _ref_to_low_high(self, ref_raw: Any) -> tuple[Optional[float], Optional[float]]:
        lo, hi, _ = self._resolve_ref(ref_raw)
        return lo, hi

    def _build_uix_snapshot_and_values(self, rows: list[dict]) -> tuple[dict, dict]:
        fields: list[dict] = []
        values: dict = {}

        for row in rows:
            param = (row.get("parameter") or "").strip()
            if not param:
                continue

            key = self._slug_key(param)

            unit = (row.get("unit") or "").strip()
            ref_raw = row.get("ref_raw")
            lo, hi = self._ref_to_low_high(ref_raw)

            f = {
                "key": key,
                "label": param,
                "unit": unit,
            }
            if lo is not None or hi is not None:
                f["ref"] = {"low": lo, "high": hi}

            # provenance (safe extra)
            if ref_raw is not None:
                f["ref_meta"] = ref_raw

            fields.append(f)

            raw_val = (row.get("result") or "").strip()
            if raw_val:
                try:
                    values[key] = float(raw_val)
                except Exception:
                    values[key] = raw_val

        # Add snapshot name for correct labeling in backend list UI
        snapshot = {
            "kind": "table",
            "name": (self.request.get("test_name") or "").strip() or None,
            "fields": fields,
        }
        return snapshot, values
