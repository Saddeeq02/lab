# apps/lab_app/features/results/views/result_table_editor.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QDialog
)

from PySide6.QtWidgets import QInputDialog
from shared.config.user_table_templates_store import UserTableTemplateStore
from shared.uix.widgets.dialogs import TableTemplatePickerDialog
from PySide6.QtWidgets import QSpinBox

from dataclasses import dataclass
from PySide6.QtWidgets import QCheckBox, QFormLayout
from PySide6.QtWidgets import QHeaderView


@dataclass
class TableFlagSchema:
    enabled: bool
    header_row: int
    col_parameter: int | None
    col_result: int | None
    col_unit: int | None
    col_ref_min: int | None
    col_ref_max: int | None
    col_flag: int | None

    def to_dict(self) -> dict:
        return {
            "enabled": bool(self.enabled),
            "header_row": int(self.header_row),
            "columns": {
                "parameter": self.col_parameter,
                "result": self.col_result,
                "unit": self.col_unit,
                "ref_min": self.col_ref_min,
                "ref_max": self.col_ref_max,
                "flag": self.col_flag,
            },
            "mode": "minmax",
        }

    @staticmethod
    def from_dict(d: dict) -> "TableFlagSchema":
        d = d or {}
        cols = (d.get("columns") or {})
        return TableFlagSchema(
            enabled=bool(d.get("enabled", False)),
            header_row=int(d.get("header_row", 0) or 0),
            col_parameter=cols.get("parameter", None),
            col_result=cols.get("result", None),
            col_unit=cols.get("unit", None),
            col_ref_min=cols.get("ref_min", None),
            col_ref_max=cols.get("ref_max", None),
            col_flag=cols.get("flag", None),
        )


class TableSchemaDialog(QDialog):
    def __init__(self, parent=None, cols: int = 2, schema: TableFlagSchema | None = None):
        super().__init__(parent)
        self.setWindowTitle("Table Auto-Flagging Schema")
        self.resize(520, 320)

        self._schema = schema or TableFlagSchema(
            enabled=False, header_row=0,
            col_parameter=0, col_result=1, col_unit=None,
            col_ref_min=None, col_ref_max=None, col_flag=None
        )

        root = QVBoxLayout(self)
        root.setSpacing(10)

        info = QLabel("Map columns so I and E system can compute flags (LOW / NORMAL / HIGH).")
        info.setWordWrap(True)
        root.addWidget(info)

        form = QFormLayout()
        root.addLayout(form)

        self.chk_enabled = QCheckBox("Enable auto-flagging for this table/template")
        self.chk_enabled.setChecked(self._schema.enabled)
        form.addRow(self.chk_enabled)

        self.spin_header = QSpinBox()
        self.spin_header.setRange(0, 10)
        self.spin_header.setValue(self._schema.header_row)
        form.addRow("Header row index:", self.spin_header)

        # Helpers
        def mk_col_combo(default_idx: int | None) -> QComboBox:
            cb = QComboBox()
            cb.addItem("(none)", None)
            for i in range(cols):
                cb.addItem(f"Col {i+1}", i)
            if default_idx is None:
                cb.setCurrentIndex(0)
            else:
                # +1 because (none) is index 0
                cb.setCurrentIndex(int(default_idx) + 1)
            return cb

        self.cb_param = mk_col_combo(self._schema.col_parameter)
        self.cb_result = mk_col_combo(self._schema.col_result)
        self.cb_unit = mk_col_combo(self._schema.col_unit)
        self.cb_refmin = mk_col_combo(self._schema.col_ref_min)
        self.cb_refmax = mk_col_combo(self._schema.col_ref_max)
        self.cb_flag = mk_col_combo(self._schema.col_flag)

        form.addRow("Parameter column:", self.cb_param)
        form.addRow("Result column:", self.cb_result)
        form.addRow("Unit column (optional):", self.cb_unit)
        form.addRow("Ref Min column:", self.cb_refmin)
        form.addRow("Ref Max column:", self.cb_refmax)
        form.addRow("Flag column:", self.cb_flag)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Save Schema")
        self.btn_ok.clicked.connect(self._on_ok)
        btns.addWidget(self.btn_ok)

        root.addLayout(btns)

    def schema(self) -> TableFlagSchema:
        return self._schema

    def _on_ok(self) -> None:
        enabled = self.chk_enabled.isChecked()
        header_row = int(self.spin_header.value())

        def v(cb: QComboBox):
            return cb.currentData()

        sch = TableFlagSchema(
            enabled=enabled,
            header_row=header_row,
            col_parameter=v(self.cb_param),
            col_result=v(self.cb_result),
            col_unit=v(self.cb_unit),
            col_ref_min=v(self.cb_refmin),
            col_ref_max=v(self.cb_refmax),
            col_flag=v(self.cb_flag),
        )

        # If enabled, enforce minimum mapping needed to compute
        if sch.enabled:
            if sch.col_result is None or sch.col_ref_min is None or sch.col_ref_max is None or sch.col_flag is None:
                QMessageBox.information(
                    self,
                    "Missing mapping",
                    "To enable auto-flagging, map Result + Ref Min + Ref Max + Flag columns."
                )
                return

        self._schema = sch
        self.accept()



class ResultTableEditorView(QWidget):
    """
    L3-3:
    - Grid selector 2x2 → 10x10
    - Auto header info
    - Editable table cells
    - Save emits payload (in-memory persistence handled by Patient Profile)
    """

    saved = Signal(dict)  # emits result payload

    def __init__(self, patient_row: dict, request: dict):
        super().__init__()
        self.patient_row = patient_row or {}
        self.request = request or {}
        
        self._flag_schema = TableFlagSchema(
            enabled=False, header_row=0,
            col_parameter=0, col_result=1, col_unit=None,
            col_ref_min=None, col_ref_max=None, col_flag=None
        )


        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Header info block
        header = QLabel(self._header_text())
        header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.setStyleSheet(
            "padding: 10px; border: 1px solid #d9d9d9; border-radius: 10px; background: #fafafa; font-weight: 600;"
        )
        root.addWidget(header)

        # Controls row
        
        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(QLabel("Grid:"))

        self.grid_combo = QComboBox()
        self._grid_sizes = [(2, 2), (4, 4), (6, 6), (8, 8), (10, 10)]
        for r, c in self._grid_sizes:
            self.grid_combo.addItem(f"{r} x {c}", (r, c))

        # Custom option exists but no popup
        self.grid_combo.addItem("Custom", ("custom", None))
        controls.addWidget(self.grid_combo)

        # ✅ Inline inputs (always visible)
        controls.addWidget(QLabel("Rows:"))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(2)
        self.rows_spin.setFixedWidth(70)
        controls.addWidget(self.rows_spin)

        controls.addWidget(QLabel("Cols:"))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 20)
        self.cols_spin.setValue(2)
        self.cols_spin.setFixedWidth(70)
        controls.addWidget(self.cols_spin)

        # Wiring
        self.grid_combo.currentIndexChanged.connect(self._on_grid_changed)
        self.rows_spin.valueChanged.connect(self._on_custom_size_changed)
        self.cols_spin.valueChanged.connect(self._on_custom_size_changed)


        controls.addStretch()

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_cells)
        controls.addWidget(self.btn_clear)

        self.btn_save = QPushButton("Save Result")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        controls.addWidget(self.btn_save)

        self.btn_save_template = QPushButton("Save as Template")
        self.btn_save_template.setCursor(Qt.PointingHandCursor)
        self.btn_save_template.clicked.connect(self._save_as_template)
        controls.addWidget(self.btn_save_template)

        self.btn_load_template = QPushButton("Load Template")
        self.btn_load_template.setCursor(Qt.PointingHandCursor)
        self.btn_load_template.clicked.connect(self._load_template)
        controls.addWidget(self.btn_load_template)

        self.btn_schema = QPushButton("Schema…")
        self.btn_schema.setCursor(Qt.PointingHandCursor)
        self.btn_schema.clicked.connect(self._edit_schema)
        controls.addWidget(self.btn_schema)

        self.btn_recompute = QPushButton("Recompute Flags")
        self.btn_recompute.setCursor(Qt.PointingHandCursor)
        self.btn_recompute.clicked.connect(self._recompute_flags)
        controls.addWidget(self.btn_recompute)

        
        root.addLayout(controls)
        
        


        # Table grid
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setVisible(True)
        self.table.setStyleSheet("QTableWidget { border: 1px solid #d9d9d9; border-radius: 8px; }")
        root.addWidget(self.table, 1)

        # Default grid
        self.grid_combo.setCurrentIndex(0)  # triggers _on_grid_changed → spins update → grid applies
        self.table.itemChanged.connect(self._enforce_header_style)
        self._auto_load_template_for_test()


    def _enforce_header_style(self, item: QTableWidgetItem) -> None:
        if item.row() == 0:
            font = item.font()
            if not font.bold():
                font.setBold(True)
                item.setFont(font)

    def _header_text(self) -> str:
        pid = self.patient_row.get("Patient ID", "-")
        name = self.patient_row.get("Name", "-")
        sex = self.patient_row.get("Sex", "-")
        age = self.patient_row.get("Age", "-")
        test = self.request.get("test_name", "Unknown Test")
        rid = self.request.get("request_id", "-")
        return f"Patient: {name} | {pid} | {sex} | {age}\nTest: {test} | Request ID: {rid}"
    
    def _bold_header_row(self, row: int = 0) -> None:
        cols = self.table.columnCount()
        for c in range(cols):
            item = self.table.item(row, c)
            if item is None:
                item = QTableWidgetItem("")
                self.table.setItem(row, c, item)

            font = item.font()
            font.setBold(True)
            item.setFont(font)


    def _on_grid_changed(self, idx: int) -> None:
        data = self.grid_combo.currentData()

        # If preset, sync spins and apply
        if isinstance(data, tuple) and len(data) == 2 and data[0] != "custom":
            r, c = data
            self.rows_spin.blockSignals(True)
            self.cols_spin.blockSignals(True)
            self.rows_spin.setValue(int(r))
            self.cols_spin.setValue(int(c))
            self.rows_spin.blockSignals(False)
            self.cols_spin.blockSignals(False)
            self._apply_grid(int(r), int(c))
            return

        # If Custom selected, apply whatever spinboxes currently say
        r = int(self.rows_spin.value())
        c = int(self.cols_spin.value())
        self._apply_grid(r, c)

    def _on_custom_size_changed(self) -> None:
        r = int(self.rows_spin.value())
        c = int(self.cols_spin.value())

        # Switch combo to Custom if user is manually changing sizes
        custom_idx = self.grid_combo.findText("Custom")
        if custom_idx >= 0 and self.grid_combo.currentIndex() != custom_idx:
            self.grid_combo.blockSignals(True)
            self.grid_combo.setCurrentIndex(custom_idx)
            self.grid_combo.blockSignals(False)

        self._apply_grid(r, c)


    def _apply_grid(self, rows: int, cols: int) -> None:
        self.table.setRowCount(rows)
        self.table.setColumnCount(cols)

        self.table.setHorizontalHeaderLabels([str(i + 1) for i in range(cols)])
        self.table.setVerticalHeaderLabels([str(i + 1) for i in range(rows)])
        
        
        # Professional spacing
        self.table.horizontalHeader().setMinimumSectionSize(120)      # min width per column
        self.table.horizontalHeader().setDefaultSectionSize(140)      # default width per column
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setMinimumWidth(520)

        # Option A: stretch to fill available space (best for reports)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Option B (alternative): keep fixed-ish columns, user can resize manually
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)


        for r in range(rows):
            for c in range(cols):
                if self.table.item(r, c) is None:
                    self.table.setItem(r, c, QTableWidgetItem(""))

        # ✅ Default bold header row
        if rows > 0:
            self._bold_header_row(0)



    def _clear_cells(self) -> None:
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item is not None:
                    item.setText("")

    def _extract_cells(self) -> list[list[str]]:
        data: list[list[str]] = []
        for r in range(self.table.rowCount()):
            row_vals: list[str] = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                row_vals.append(item.text().strip() if item else "")
            data.append(row_vals)
        return data
    
    def load_payload(self, payload: dict) -> None:
        """
        Prefill table grid from a previously saved payload.
        """
        grid = payload.get("grid", {})
        self._apply_schema_from_grid(grid)

        rows = int(grid.get("rows", 2))
        cols = int(grid.get("cols", 2))
        cells = grid.get("cells", [])

        # Apply grid size first
        self._apply_grid(rows, cols)
        
        col_headers = grid.get("col_headers")
        row_headers = grid.get("row_headers")
        if isinstance(col_headers, list) and len(col_headers) == cols:
            self.table.setHorizontalHeaderLabels([str(x) for x in col_headers])
        if isinstance(row_headers, list) and len(row_headers) == rows:
            self.table.setVerticalHeaderLabels([str(x) for x in row_headers])


        # Fill cells
        for r in range(min(rows, len(cells))):
            for c in range(min(cols, len(cells[r]))):
                item = self.table.item(r, c)
                if item is None:
                    item = QTableWidgetItem("")
                    self.table.setItem(r, c, item)
                item.setText(str(cells[r][c]))
                
        # Ensure header row stays bold
        if rows > 0:
            self._bold_header_row(0)
            
        if getattr(self, "_flag_schema", None) and self._flag_schema.enabled:
            self._recompute_flags()


                
    def _load_template(self) -> None:
        dlg = TableTemplatePickerDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        tid = dlg.selected_template_id()
        if not tid:
            return

        items = UserTableTemplateStore.load_all()
        found = next((t for t in items if t.id == tid), None)
        if not found:
            QMessageBox.warning(self, "Not found", "Template not found.")
            return

        payload = {"grid": found.grid}
        self.load_payload(payload)  # uses your existing load_payload method
        QMessageBox.information(self, "Loaded", f"Loaded template: {found.name}")

                
    def _save_as_template(self) -> None:
        # Default suggestion: request test name
        default_test = str(self.request.get("test_name", "")).strip()

        name, ok = QInputDialog.getText(self, "Save Table Template", "Template Name:", text=default_test)
        if not ok or not name.strip():
            return

        test_name, ok2 = QInputDialog.getText(self, "Save Table Template", "Test Name (search key):", text=default_test)
        if not ok2 or not test_name.strip():
            return

        grid = self._snapshot_grid()
        tpl = UserTableTemplateStore.create(name=name, test_name=test_name, grid=grid)
        UserTableTemplateStore.upsert(tpl)

        QMessageBox.information(self, "Saved", "Table template saved. You can load it later by searching the test name.")



    def _save(self) -> None:
        cells = self._extract_cells()

        any_text = any(any(cell for cell in row) for row in cells)
        if not any_text:
            QMessageBox.information(self, "Nothing to save", "Please enter at least one value before saving.")
            return

        # -------------------------
        # UIX snapshot (canonical)
        # -------------------------
        snapshot = {
            "kind": "grid",
            "grid": {
                "rows": self.table.rowCount(),
                "cols": self.table.columnCount(),
                "col_headers": [
                    self.table.horizontalHeaderItem(i).text()
                    if self.table.horizontalHeaderItem(i) else str(i + 1)
                    for i in range(self.table.columnCount())
                ],
                "row_headers": [
                    self.table.verticalHeaderItem(i).text()
                    if self.table.verticalHeaderItem(i) else str(i + 1)
                    for i in range(self.table.rowCount())
                ],
            }
        }

        # -------------------------
        # Values (UIX-first)
        # -------------------------
        values = {
            "cells": cells
        }

        # -------------------------
        # Local grid mirror
        # -------------------------
        grid_block = {
            "rows": self.table.rowCount(),
            "cols": self.table.columnCount(),
            "cells": cells,
        }

        # ✅ mirror schema everywhere
        if getattr(self, "_flag_schema", None):
            schema_dict = self._flag_schema.to_dict()
            snapshot["schema"] = schema_dict
            grid_block["schema"] = schema_dict
            grid_block["col_headers"] = snapshot["grid"]["col_headers"]
            grid_block["row_headers"] = snapshot["grid"]["row_headers"]
            
        # ✅ Auto-apply flags into cells before saving (if enabled)
        try:
            if getattr(self, "_flag_schema", None) and self._flag_schema.enabled:
                from apps.lab_app.features.results.services.compute_service import compute_grid_flags_and_apply
                values, grid_flags = compute_grid_flags_and_apply(
                    template_snapshot=snapshot,
                    values=values,
                )
                # keep grid mirror aligned with updated cells
                grid_block["cells"] = (values or {}).get("cells") or grid_block.get("cells") or []
                # optional: persist flags summary in UIX (nice for debugging/preview)
                # payload_uix_flags = grid_flags
        except Exception:
            # never block save because of flagging
            pass


        # -------------------------
        # Final payload
        # -------------------------
        payload = {
            "type": "table",
            "patient": dict(self.patient_row),
            "request": dict(self.request),

            "uix": {
                "test_type_id": self.request.get("test_type_id"),
                "template_id": None,
                "template_snapshot": snapshot,
                "values": values,
            },

            "grid": grid_block,
            "status": "draft",
            "notes": "",
        }

        print(f"UIX_TABLE_SAVE rows={snapshot['grid']['rows']} cols={snapshot['grid']['cols']}")

        self.saved.emit(payload)
        QMessageBox.information(self, "Saved", "Table result saved (draft).")

    def _snapshot_grid(self) -> dict:
        rows = self.table.rowCount()
        cols = self.table.columnCount()

        cells: list[list[str]] = []
        for r in range(rows):
            row_cells: list[str] = []
            for c in range(cols):
                it = self.table.item(r, c)
                row_cells.append(it.text() if it else "")
            cells.append(row_cells)

        col_headers = [
            self.table.horizontalHeaderItem(i).text() if self.table.horizontalHeaderItem(i) else str(i + 1)
            for i in range(cols)
        ]
        row_headers = [
            self.table.verticalHeaderItem(i).text() if self.table.verticalHeaderItem(i) else str(i + 1)
            for i in range(rows)
        ]

        grid = {
            "rows": rows,
            "cols": cols,
            "cells": cells,
            "col_headers": col_headers,
            "row_headers": row_headers,
        }
        # ✅ persist schema into template grid
        if getattr(self, "_flag_schema", None):
            grid["schema"] = self._flag_schema.to_dict()
        return grid

        
        

    def _auto_load_template_for_test(self) -> None:
        test_name = (self.request.get("test_name") or "").strip().lower()
        if not test_name:
            return

        items = UserTableTemplateStore.load_all()
        # match by saved test_name search key
        found = next((t for t in items if (t.test_name or "").strip().lower() == test_name), None)
        if not found:
            return

        self.load_payload({"grid": found.grid})
        
        
    def _current_schema_dict(self) -> dict | None:
        if not getattr(self, "_flag_schema", None):
            return None
        return self._flag_schema.to_dict()

    def _apply_schema_from_grid(self, grid: dict) -> None:
        # schema may live under grid["schema"] or under payload["uix"]["template_snapshot"]["schema"]
        sch = (grid or {}).get("schema") or {}
        self._flag_schema = TableFlagSchema.from_dict(sch)

    def _edit_schema(self) -> None:
        cols = int(self.table.columnCount() or 0)
        if cols <= 0:
            QMessageBox.information(self, "No grid", "Create a grid first.")
            return

        dlg = TableSchemaDialog(self, cols=cols, schema=self._flag_schema)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self._flag_schema = dlg.schema()
        QMessageBox.information(self, "Saved", "Schema saved for this table. You can now recompute flags.")
        if self._flag_schema.enabled:
            self._recompute_flags()

    def _recompute_flags(self) -> None:
        sch = getattr(self, "_flag_schema", None)
        if not sch or not sch.enabled:
            QMessageBox.information(self, "Schema not enabled", "Enable auto-flagging in Schema… first.")
            return

        from apps.lab_app.features.results.services.compute_service import compute_grid_flags_and_apply

        # Build canonical snapshot + values (same as Save)
        snapshot = {
            "kind": "grid",
            "grid": {
                "rows": self.table.rowCount(),
                "cols": self.table.columnCount(),
                "col_headers": [
                    self.table.horizontalHeaderItem(i).text()
                    if self.table.horizontalHeaderItem(i) else str(i + 1)
                    for i in range(self.table.columnCount())
                ],
                "row_headers": [
                    self.table.verticalHeaderItem(i).text()
                    if self.table.verticalHeaderItem(i) else str(i + 1)
                    for i in range(self.table.rowCount())
                ],
            },
            "schema": sch.to_dict(),
        }

        values = {"cells": self._extract_cells()}

        updated_values, flags = compute_grid_flags_and_apply(
            template_snapshot=snapshot,
            values=values,
        )

        # Apply updated cells back into the QTableWidget
        cells = (updated_values or {}).get("cells") or []
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                it = self.table.item(r, c)
                if it is None:
                    it = QTableWidgetItem("")
                    self.table.setItem(r, c, it)

                txt = ""
                if r < len(cells) and isinstance(cells[r], list) and c < len(cells[r]):
                    txt = str(cells[r][c] or "")
                it.setText(txt)
        self.table.blockSignals(False)

        # Keep header row bold after recompute
        if self.table.rowCount() > 0:
            self._bold_header_row(0)

        changed = int((flags or {}).get("changed_cells", 0) or 0)
        QMessageBox.information(self, "Done", f"Recomputed flags for {changed} cell(s).")