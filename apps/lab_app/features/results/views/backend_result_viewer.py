# apps/lab_app/features/results/views/backend_result_viewer.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTextEdit, QHeaderView
)
from PySide6.QtCore import Qt

from shared.net.api_client import ApiClient, ApiError


class BackendResultViewerDialog(QDialog):
    def __init__(self, result_id: int, api: ApiClient, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Backend Result #{result_id}")
        self.resize(900, 520)

        root = QVBoxLayout(self)
        root.setSpacing(8)

        try:
            result = api.get_json(f"/api/results/{result_id}")
        except ApiError as e:
            root.addWidget(QLabel(f"Failed to load result: {e}"))
            return

        status = result.get("status", "")
        created_at = result.get("created_at", "")
        updated_at = result.get("updated_at", "")

        root.addWidget(QLabel(
            f"Status: {status}  |  Created: {created_at}  |  Updated: {updated_at}"
        ))

        snapshot = result.get("template_snapshot") or {}
        values = result.get("values") or {}
        flags = result.get("flags") or {}

        kind = (snapshot.get("kind") or "").strip().lower()

        # -----------------------------
        # Structured/Table snapshot view
        # -----------------------------
        if kind == "table":
            fields = snapshot.get("fields") or []

            table = QTableWidget()
            table.setRowCount(len(fields))
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Parameter", "Result", "Unit", "Ref. Range", "Flag"])
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setStretchLastSection(True)

            for r, f in enumerate(fields):
                if not isinstance(f, dict):
                    continue

                key = f.get("key") or ""
                label = f.get("label") or (key.upper() if key else "")

                # Result value
                val = "" if not key else values.get(key, "")
                val_text = "" if val is None else str(val)

                # Unit
                unit_text = str(f.get("unit", "") or "")

                # Ref range from snapshot ref.low/ref.high
                ref = f.get("ref") or {}
                lo = ref.get("low")
                hi = ref.get("high")
                if lo is None and hi is None:
                    ref_text = "—"
                else:
                    if lo is not None and hi is not None:
                        ref_text = f"{lo} - {hi}"
                    elif lo is not None:
                        ref_text = f">= {lo}"
                    else:
                        ref_text = f"<= {hi}"

                # Flag (computed by backend)
                flag = flags.get(key) if key else None
                state = (flag.get("state") if isinstance(flag, dict) else "") or ""
                state_norm = str(state).lower().strip()

                table.setItem(r, 0, QTableWidgetItem(label))
                table.setItem(r, 1, QTableWidgetItem(val_text))
                table.setItem(r, 2, QTableWidgetItem(unit_text))
                table.setItem(r, 3, QTableWidgetItem(ref_text))

                it4 = QTableWidgetItem(state_norm if state_norm else "—")
                if state_norm == "high":
                    it4.setForeground(Qt.red)
                elif state_norm == "low":
                    it4.setForeground(Qt.blue)
                table.setItem(r, 4, it4)

            # Do this ONCE:
            table.resizeColumnsToContents()

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)            # Parameter
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # Result
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # Unit
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Ref. Range
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Flag

            root.addWidget(table)

        # -----------------------------
        # Grid (Table editor) snapshot view
        # -----------------------------
        elif kind == "grid":
            grid = snapshot.get("grid") or {}
            rows = int(grid.get("rows", 0) or 0)
            cols = int(grid.get("cols", 0) or 0)

            col_headers = grid.get("col_headers") or [str(i + 1) for i in range(cols)]
            row_headers = grid.get("row_headers") or [str(i + 1) for i in range(rows)]

            # values for grid are expected as: {"cells": [[...], ...]}
            cells = []
            if isinstance(values, dict):
                cells = values.get("cells") or []
            if not isinstance(cells, list):
                cells = []

            table = QTableWidget()
            table.setRowCount(rows)
            table.setColumnCount(cols)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.setAlternatingRowColors(True)

            table.setHorizontalHeaderLabels([str(x) for x in col_headers[:cols]])
            table.setVerticalHeaderLabels([str(x) for x in row_headers[:rows]])

            for r in range(rows):
                for c in range(cols):
                    v = ""
                    if r < len(cells) and isinstance(cells[r], list) and c < len(cells[r]):
                        v = "" if cells[r][c] is None else str(cells[r][c])
                    table.setItem(r, c, QTableWidgetItem(v))

            table.resizeColumnsToContents()
            root.addWidget(table)

        else:
            root.addWidget(QLabel(f"Unsupported snapshot kind: {kind or '—'}"))

        # --- Notes (always render) ---
        root.addWidget(QLabel("Notes"))
        notes_text = result.get("notes") or ""
        notes_box = QTextEdit(notes_text)
        notes_box.setReadOnly(True)
        notes_box.setMinimumHeight(120)
        root.addWidget(notes_box)
