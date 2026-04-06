from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton,
    QHBoxLayout, QFileDialog, QMessageBox, QCheckBox, QComboBox, QDoubleSpinBox,
    QFrame
)

from shared.config.lab_profile import LabProfile
from shared.config.backend_profile import BackendProfile
from shared.net.api_client import ApiClient, ApiConfig, ApiError


class _HealthWorker(QObject):
    finished = Signal(dict)        # {"health":..., "db":...}
    failed = Signal(str)

    def __init__(self, base_url: str, timeout_s: float):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s

    def run(self):
        try:
            api = ApiClient(ApiConfig(
                base_url=self.base_url,
                timeout_s=self.timeout_s
            ))
            h = api.health()
            d = api.health_db()
            self.finished.emit({"health": h, "db": d})
        except ApiError as e:
            # include payload when available
            extra = ""
            if e.payload is not None:
                extra = f"\n\nDetails: {e.payload}"
            self.failed.emit(f"{str(e)}{extra}")
        except Exception as e:
            self.failed.emit(str(e))


class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.profile = LabProfile.load()
        self.backend = BackendProfile.load()

        root = QVBoxLayout(self)
        root.setSpacing(10)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 14px; font-weight: 800;")
        root.addWidget(title)

        # ----------------------------
        # Lab Profile (existing)
        # ----------------------------
        sub = QLabel("Lab Profile (used on printed reports).")
        sub.setStyleSheet("color: #666;")
        root.addWidget(sub)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)

        self.lab_name = QLineEdit(self.profile.lab_name)
        self.address = QLineEdit(self.profile.address)
        self.phone = QLineEdit(self.profile.phone)
        self.email = QLineEdit(self.profile.email)

        self.logo_path = QLineEdit(self.profile.logo_path)
        self.logo_path.setPlaceholderText("Select a logo file (optional)")
        self.logo_path.setReadOnly(True)

        browse_row = QHBoxLayout()
        browse_row.addWidget(self.logo_path, 1)

        self.btn_browse = QPushButton("Browse")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._browse_logo)
        browse_row.addWidget(self.btn_browse)

        self.watermark_enabled = QCheckBox("Enable watermark using logo")
        self.watermark_enabled.setChecked(bool(self.profile.watermark_enabled))

        form.addRow("Lab name", self.lab_name)
        form.addRow("Address", self.address)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)

        self.scientist_name = QLineEdit(self.profile.scientist_name)
        self.scientist_qualification = QLineEdit(self.profile.scientist_qualification)
        self.report_notes = QLineEdit(self.profile.report_notes)

        form.addRow("Scientist Name", self.scientist_name)
        form.addRow("Qualification (e.g. MLS)", self.scientist_qualification)
        form.addRow("Report Notes", self.report_notes)

        form.addRow("Logo", browse_row)
        form.addRow("", self.watermark_enabled)

        root.addLayout(form)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setFrameShadow(QFrame.Sunken)
        root.addWidget(div)

        # ----------------------------
        # Backend Integration (NEW)
        # ----------------------------
        sub2 = QLabel("Backend Integration (Option A: read-only first).")
        sub2.setStyleSheet("color: #666;")
        root.addWidget(sub2)

        bform = QFormLayout()
        bform.setLabelAlignment(Qt.AlignLeft)

        self.backend_enabled = QCheckBox("Enable backend integration")
        self.backend_enabled.setChecked(bool(self.backend.enabled))

        self.backend_url = QLineEdit(self.backend.base_url)
        self.backend_url.setPlaceholderText("https://iandelaboratory.up.railway.app")

        self.backend_role = QComboBox()
        self.backend_role.addItems(["labtech", "supervisor", "admin"])
        idx = self.backend_role.findText(self.backend.role)
        self.backend_role.setCurrentIndex(idx if idx >= 0 else 0)

        self.backend_timeout = QDoubleSpinBox()
        self.backend_timeout.setRange(1.0, 30.0)
        self.backend_timeout.setDecimals(1)
        self.backend_timeout.setSingleStep(0.5)
        self.backend_timeout.setValue(float(self.backend.timeout_s))

        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setCursor(Qt.PointingHandCursor)
        self.btn_test.clicked.connect(self._test_connection)

        self.test_status = QLabel("Not tested")
        self.test_status.setStyleSheet("color: #666;")

        test_row = QHBoxLayout()
        test_row.addWidget(self.btn_test)
        test_row.addWidget(self.test_status, 1)

        bform.addRow("", self.backend_enabled)
        bform.addRow("Base URL", self.backend_url)
        bform.addRow("Role header", self.backend_role)
        bform.addRow("Timeout (sec)", self.backend_timeout)
        bform.addRow("Connection", test_row)

        root.addLayout(bform)

        # Save row
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)

        root.addLayout(btn_row)
        root.addStretch()

        # Worker thread references (avoid GC)
        self._thread: QThread | None = None
        self._worker: _HealthWorker | None = None

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Lab Logo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self.logo_path.setText(path)

    def _save(self):
        # --- Lab profile ---
        self.profile.lab_name = self.lab_name.text().strip() or self.profile.lab_name
        self.profile.address = self.address.text().strip() or self.profile.address
        self.profile.phone = self.phone.text().strip()
        self.profile.email = self.email.text().strip()
        self.profile.logo_path = self.logo_path.text().strip()
        self.profile.watermark_enabled = self.watermark_enabled.isChecked()
        self.profile.scientist_name = self.scientist_name.text().strip()
        self.profile.scientist_qualification = self.scientist_qualification.text().strip()
        self.profile.report_notes = self.report_notes.text().strip()
        self.profile.save()

        # --- Backend profile ---
        self.backend.enabled = self.backend_enabled.isChecked()
        self.backend.base_url = self.backend_url.text().strip() or self.backend.base_url
        self.backend.role = self.backend_role.currentText().strip().lower() or "labtech"
        self.backend.timeout_s = float(self.backend_timeout.value())
        self.backend.save()

        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def _test_connection(self):
        base_url = self.backend_url.text().strip() or "https://iandelaboratory.up.railway.app/"
        role = self.backend_role.currentText().strip().lower() or "labtech"
        timeout_s = float(self.backend_timeout.value())

        self.btn_test.setEnabled(False)
        self.test_status.setText("Testing...")
        self.test_status.setStyleSheet("color: #666;")

        # teardown previous thread if any
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(200)
            except Exception:
                pass
            self._thread = None
            self._worker = None

        self._thread = QThread()
        self._worker = _HealthWorker(base_url=base_url, timeout_s=timeout_s)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_test_ok)
        self._worker.failed.connect(self._on_test_fail)

        # cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_test_done)

        self._thread.start()

    def _on_test_ok(self, data: dict):
        h = data.get("health")
        d = data.get("db")
        self.test_status.setStyleSheet("color: #0a7;")
        self.test_status.setText(f"OK  •  health={h}  •  db={d}")

    def _on_test_fail(self, msg: str):
        self.test_status.setStyleSheet("color: #a00;")
        self.test_status.setText("FAILED")
        QMessageBox.warning(self, "Connection Failed", msg)

    def _on_test_done(self):
        self.btn_test.setEnabled(True)
