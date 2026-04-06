from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView
from shared.config.user_table_templates_store import UserTableTemplateStore


from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFrame
)
from PySide6.QtCore import Qt

class TemplateBuilderDialog(QDialog):
    """
    Phase-1 Laboratory Template Builder:
    - Structured numeric range enforcement.
    - Enterprise Blue-Black styling.
    """
    def __init__(self, parent=None, name: str = "", parameters: list[dict] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Structured Template Editor")
        self.resize(850, 600)
        self.setObjectName("TemplateDialog")

        self._saved = False
        self._template_name = name or ""
        self._parameters = parameters or []

        # Main Layout
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # Header Section
        header_label = QLabel("Template Configuration")
        header_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        root.addWidget(header_label)

        # Name Input Card
        name_card = QFrame()
        name_card.setStyleSheet("background: white; border: 1px solid #E2E8F0; border-radius: 8px;")
        name_layout = QHBoxLayout(name_card)
        name_layout.setContentsMargins(15, 10, 15, 10)
        
        name_layout.addWidget(QLabel("Template Name:"))
        self.name_edit = QLineEdit(self._template_name)
        self.name_edit.setPlaceholderText("e.g., Full Blood Count Standard")
        self.name_edit.setStyleSheet("border: 1.5px solid #CBD5E1; padding: 6px;")
        name_layout.addWidget(self.name_edit, 1)
        root.addWidget(name_card)

        # Table: Parameter | Unit | Ref Min | Ref Max
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Parameter Name", "Unit", "Ref Min (Low)", "Ref Max (High)"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False) # Modern cleaner look
        
        # Header Styling
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setStyleSheet("font-weight: bold; background-color: #F8FAFC;")
        
        root.addWidget(self.table, 1)

        # Action Buttons Section
        btns_row = QHBoxLayout()
        
        # Row Management
        self.btn_add = QPushButton("+ Add Parameter")
        self.btn_add.setObjectName("SecondaryAction")
        self.btn_add.clicked.connect(self._add_row)
        btns_row.addWidget(self.btn_add)

        self.btn_remove = QPushButton("- Remove Selected")
        self.btn_remove.setObjectName("DangerAction")
        self.btn_remove.clicked.connect(self._remove_row)
        btns_row.addWidget(self.btn_remove)

        btns_row.addStretch()

        # Dialog Controls
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.reject)
        btns_row.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Save Template")
        self.btn_save.setFixedWidth(150)
        self.btn_save.setProperty("variant", "primary") # Triggering our Blue button
        self.btn_save.clicked.connect(self._save)
        btns_row.addWidget(self.btn_save)

        root.addLayout(btns_row)
        self._load_rows(self._parameters)


    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(4):
            self.table.setItem(r, c, QTableWidgetItem(""))

    def _remove_row(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)

    def _load_rows(self, params: list[dict]):
        self.table.setRowCount(0)
        if not params:
            self._add_row()
            return

        for p in params:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(p.get("name", ""))))
            self.table.setItem(r, 1, QTableWidgetItem(str(p.get("unit", ""))))
            ref = p.get("ref")
            lo, hi = "", ""
            if isinstance(ref, (list, tuple)) and len(ref) == 2:
                lo, hi = str(ref[0]), str(ref[1])
            self.table.setItem(r, 2, QTableWidgetItem(lo))
            self.table.setItem(r, 3, QTableWidgetItem(hi))

    def is_saved(self) -> bool:
        return self._saved

    def template_name(self) -> str:
        return self._template_name

    def parameters(self) -> list[dict]:
        return self._parameters

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.information(self, "Missing name", "Please provide a template name.")
            return

        params: list[dict] = []
        for r in range(self.table.rowCount()):
            pname = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            unit = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            lo_s = (self.table.item(r, 2).text() if self.table.item(r, 2) else "").strip()
            hi_s = (self.table.item(r, 3).text() if self.table.item(r, 3) else "").strip()

            if not pname:
                continue  # ignore empty rows

            # Enforce numeric ref ranges to keep auto-flagging consistent
            try:
                lo = float(lo_s)
                hi = float(hi_s)
            except Exception:
                QMessageBox.information(
                    self,
                    "Invalid ref range",
                    f"Row {r+1}: Ref Min/Max must be numeric to support auto-flagging."
                )
                return

            if lo > hi:
                QMessageBox.information(
                    self,
                    "Invalid ref range",
                    f"Row {r+1}: Ref Min cannot be greater than Ref Max."
                )
                return

            params.append({"name": pname, "unit": unit, "ref": (lo, hi)})

        if not params:
            QMessageBox.information(self, "No parameters", "Add at least one parameter row.")
            return

        self._template_name = name
        self._parameters = params
        self._saved = True
        self.accept()



class TableTemplatePickerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Load Laboratory Template")
        self.resize(750, 480)

        self._selected_id: str | None = None
        self._items = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(15)

        # Search bar area
        search_container = QFrame()
        search_container.setStyleSheet("background: #F1F5F9; border-radius: 8px;")
        search_layout = QHBoxLayout(search_container)
        
        search_layout.addWidget(QLabel("Find Template:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by test name or template...")
        self.search_edit.setStyleSheet("border: 1px solid #CBD5E1; padding: 8px; background: white;")
        search_layout.addWidget(self.search_edit, 1)
        
        self.btn_refresh = QPushButton("Search")
        self.btn_refresh.setProperty("variant", "primary")
        self.btn_refresh.clicked.connect(self._refresh)
        search_layout.addWidget(self.btn_refresh)
        
        root.addWidget(search_container)

        # Results Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Template Name", "Mapped Test", "Dimensions", "Last Updated"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        # Bottom Bar
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.btn_cancel = QPushButton("Close")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_load = QPushButton("Load Selected Template")
        self.btn_load.setProperty("variant", "primary")
        self.btn_load.clicked.connect(self._load)
        btns.addWidget(self.btn_load)
        
        root.addLayout(btns)

        # Event connections
        self.search_edit.returnPressed.connect(self._refresh)
        self.table.itemDoubleClicked.connect(lambda _: self._load())
        self._refresh()


    def selected_template_id(self) -> str | None:
        return self._selected_id

    def _refresh(self):
        q = self.search_edit.text().strip()
        items = UserTableTemplateStore.search(q)

        self.table.setRowCount(len(items))
        self._items = items

        for r, t in enumerate(items):
            grid = t.grid or {}
            rows = int(grid.get("rows", 0) or 0)
            cols = int(grid.get("cols", 0) or 0)
            grid_txt = f"{rows}×{cols}" if rows and cols else "-"

            self.table.setItem(r, 0, QTableWidgetItem(t.name))
            self.table.setItem(r, 1, QTableWidgetItem(t.test_name))
            self.table.setItem(r, 2, QTableWidgetItem(grid_txt))
            self.table.setItem(r, 3, QTableWidgetItem(t.updated_at))


        self.table.resizeColumnsToContents()

    def _load(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._items):
            QMessageBox.information(self, "No selection", "Select a template first.")
            return
        self._selected_id = self._items[row].id
        self.accept()
