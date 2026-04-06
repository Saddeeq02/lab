# -*- coding: utf-8 -*-
# apps/lab_app/features/test_types/views/test_types_view.py
from __future__ import annotations

from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox, QLineEdit, QDialog, QFormLayout
)

from shared.uix.widgets.tables import DataTable
from shared.config.backend_profile import BackendProfile
from shared.net.api_client import ApiClient, ApiConfig, ApiError
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QDoubleSpinBox

class _LoadTestTypesWorker(QObject):
    finished = Signal(list)   # list[dict]
    failed = Signal(str)

    def __init__(self, base_url: str, timeout_s: float):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s

    def run(self):
        try:
            api = ApiClient(ApiConfig(base_url=self.base_url, timeout_s=self.timeout_s))
            data = api.get_json("/api/test-types")

            if isinstance(data, dict):
                rows = data.get("value", [])
            elif isinstance(data, list):
                rows = data
            else:
                rows = []

            self.finished.emit(rows)
        except ApiError as e:
            extra = f"\n\nDetails: {e.payload}" if getattr(e, "payload", None) is not None else ""
            self.failed.emit(f"{str(e)}{extra}")
        except Exception as e:
            self.failed.emit(str(e))


class _CreateTestTypeWorker(QObject):
    finished = Signal(dict)   # created row
    failed = Signal(str)

    def __init__(self, base_url: str, timeout_s: float, name: str, code: str, price: float):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.name = name
        self.code = code
        self.price = price

    def run(self):
        try:
            api = ApiClient(ApiConfig(base_url=self.base_url, timeout_s=self.timeout_s))
            body = {"name": self.name, "code": self.code, "price" : self.price}
            created = api.post_json("/api/test-types", body=body)
            self.finished.emit(created if isinstance(created, dict) else {})
        except ApiError as e:
            extra = f"\n\nDetails: {e.payload}" if getattr(e, "payload", None) is not None else ""
            self.failed.emit(f"{str(e)}{extra}")
        except Exception as e:
            self.failed.emit(str(e))


class CreateTestTypeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Test Type")
        self.resize(520, 220)

        root = QVBoxLayout(self)

        form = QFormLayout()
        self.name = QLineEdit()
        self.code = QLineEdit()
        self.code.setPlaceholderText("e.g. WIDAL, FBC, MP, URINALYSIS")

        self.price = QDoubleSpinBox()
        self.price.setMaximum(100000000)
        self.price.setDecimals(2)
        self.price.setPrefix("₦ ")
        self.price.setValue(0)

        form.addRow("Name", self.name)
        form.addRow("Code", self.code)
        form.addRow("Price", self.price)
        root.addLayout(form)

        

        btns = QHBoxLayout()
        btns.addStretch(1)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)

        self.btn_create = QPushButton("Create")
        self.btn_create.setObjectName("Primary")
        self.btn_create.clicked.connect(self._on_create)
        btns.addWidget(self.btn_create)

        

        root.addLayout(btns)

    def _on_create(self):
        n = self.name.text().strip()
        c = self.code.text().strip()
        p = self.price.value()

        if not n or not c:
            QMessageBox.information(self, "Missing fields", "Name and Code are required.")
            return

        if p <= 0:
            QMessageBox.information(self, "Invalid price", "Price must be greater than zero.")
            return

        self.accept()

    def payload(self) -> tuple[str, str, float]:
        return (
            self.name.text().strip(),
            self.code.text().strip(),
            self.price.value(),
        )

class TestTypesView(QWidget):
    def __init__(self):
        super().__init__()

        self._thread: QThread | None = None
        self._worker: QObject | None = None
        self._pending_refresh = False
        self._last_created: dict | None = None


        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("Panel2")
        h = QHBoxLayout(header)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(10)

        title = QLabel("Test Types")
        title.setStyleSheet("font-size: 13pt; font-weight: 800;")
        h.addWidget(title)

        hint = QLabel("Create and manage tests available to Receptionist/Cashier.")
        hint.setObjectName("Muted")
        h.addWidget(hint)

        h.addStretch(1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh)
        h.addWidget(self.btn_refresh)

        self.btn_new = QPushButton("New Test Type")
        self.btn_new.setObjectName("Primary")
        self.btn_new.clicked.connect(self._new_test_type)
        h.addWidget(self.btn_new)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.clicked.connect(self._edit_test_type)
        h.addWidget(self.btn_edit)


        root.addWidget(header)

        panel = QFrame()
        panel.setObjectName("Panel")
        p = QVBoxLayout(panel)
        p.setContentsMargins(14, 14, 14, 14)
        p.setSpacing(10)

        cols = ["ID", "Name", "Code", "price", "Created At"]
        self.table = DataTable(columns=cols)
        p.addWidget(self.table, 1)

        self.status = QLabel("Not loaded")
        self.status.setObjectName("Muted")
        p.addWidget(self.status)

        root.addWidget(panel, 1)

        self.refresh()

    def refresh(self):
        bp = BackendProfile.load()
        if not bp.enabled:
            self.status.setText("Backend integration is disabled in Settings.")
            return

        self.btn_refresh.setEnabled(False)
        self.btn_new.setEnabled(False)
        self.status.setText("Loading test types...")

        self._stop_thread()

        self._thread = QThread()
        self._worker = _LoadTestTypesWorker(bp.base_url, bp.timeout_s)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_done)

        self._thread.start()

    
    def _new_test_type(self):
        bp = BackendProfile.load()
        if not bp.enabled:
            QMessageBox.information(self, "Disabled", "Enable backend integration in Settings first.")
            return

        dlg = CreateTestTypeDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        name, code, price = dlg.payload()

        self.btn_refresh.setEnabled(False)
        self.btn_new.setEnabled(False)
        self.status.setText("Creating test type...")
        self._pending_refresh = True
        self._last_created = None

        self._stop_thread()

        self._thread = QThread()
        self._worker = _CreateTestTypeWorker(bp.base_url, bp.timeout_s, name=name, code=code, price=price)
        self._worker.moveToThread(self._thread)

        def on_created(created: dict):
            # store result; DO NOT refresh here
            self._last_created = created if isinstance(created, dict) else {}
            self.status.setText("Created. Updating list...")

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(on_created)
        self._worker.failed.connect(self._on_failed)

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)

        self._thread.finished.connect(self._on_done)

        # good hygiene (prevents Qt object buildup)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)

        self._thread.start()



    def _edit_test_type(self):

        row_index = self.table.currentRow()

        if row_index < 0:
            QMessageBox.information(self, "Select", "Select a test type first.")
            return

        row = self.table._rows[row_index]

        dlg = EditTestTypeDialog(row, self)

        if dlg.exec() != QDialog.Accepted:
            return

        body = dlg.payload()
        test_id = row["_raw"]["id"]

        bp = BackendProfile.load()

        self._thread = QThread()
        self._worker = _UpdateTestTypeWorker(
            bp.base_url,
            bp.timeout_s,
            test_id,
            body
        )

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(lambda _: self.refresh())
        self._worker.failed.connect(self._on_failed)

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)

        self._thread.start()


    def _on_loaded(self, rows: list):
        out = []
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            out.append({
                "ID": r.get("id"),
                "Name": r.get("name"),
                "Code": r.get("code"),
                "price": f"₦ {r.get('price')}",
                "Created At": r.get("created_at"),
                "_raw": r,
            })
        self.table.set_rows(out)
        self.status.setText(f"Loaded {len(out)} test type(s).")

    def _on_failed(self, msg: str):
        self.status.setText("Operation failed.")
        QMessageBox.warning(self, "Backend Error", msg)

    def _on_done(self):
        self.btn_refresh.setEnabled(True)
        self.btn_new.setEnabled(True)

        if getattr(self, "_pending_refresh", False):
            self._pending_refresh = False
            # schedule on next UI tick (extra safety)
            QTimer.singleShot(0, self.refresh)

    def _stop_thread(self):
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(1500)
            except Exception:
                pass
            self._thread = None
            self._worker = None




class EditTestTypeDialog(QDialog):

    def __init__(self, row: dict, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Edit Test Type")
        self.resize(520, 220)

        raw = row.get("_raw", {})

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(raw.get("name"))
        self.code = QLineEdit(raw.get("code"))

        self.price = QDoubleSpinBox()
        self.price.setMaximum(100000000)
        self.price.setDecimals(2)
        self.price.setPrefix("₦ ")
        self.price.setValue(float(raw.get("price", 0)))

        form.addRow("Name", self.name)
        form.addRow("Code", self.code)
        form.addRow("Price", self.price)

        root.addLayout(form)

        btns = QHBoxLayout()
        btns.addStretch()

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)

        save = QPushButton("Save Changes")
        save.setObjectName("Primary")
        save.clicked.connect(self.accept)

        btns.addWidget(cancel)
        btns.addWidget(save)

        root.addLayout(btns)

    def payload(self):
        return {
            "name": self.name.text().strip(),
            "code": self.code.text().strip(),
            "price": self.price.value(),
        }
    




class _UpdateTestTypeWorker(QObject):

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, base_url, timeout_s, test_id, body):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.test_id = test_id
        self.body = body

    def run(self):
        try:
            api = ApiClient(ApiConfig(base_url=self.base_url, timeout_s=self.timeout_s))

            updated = api.patch_json(
                f"/api/test-types/{self.test_id}",
                body=self.body
            )

            self.finished.emit(updated if isinstance(updated, dict) else {})

        except ApiError as e:
            extra = f"\n\nDetails: {e.payload}" if getattr(e, "payload", None) else ""
            self.failed.emit(f"{str(e)}{extra}")

        except Exception as e:
            self.failed.emit(str(e))