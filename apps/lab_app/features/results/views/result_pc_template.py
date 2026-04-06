# apps/lab_app/features/results/views/result_pc_template.py
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QTextEdit
)

from shared.config.lab_profile import LabProfile
from apps.lab_app.features.results.services.template_service import build_context, render_placeholders


class PCTemplateResultView(QWidget):
    saved = Signal(dict)

    def __init__(self, patient_row: dict, request: dict):
        super().__init__()
        self.patient_row = patient_row or {}
        self.request = request or {}

        self.template_path: str = ""
        self.rendered: str = ""

        root = QVBoxLayout(self)
        root.setSpacing(10)

        header = QLabel(self._header_text())
        header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.setStyleSheet(
            "padding: 10px; border: 1px solid #d9d9d9; border-radius: 10px; background: #fafafa; font-weight: 600;"
        )
        root.addWidget(header)

        # Controls
        row = QHBoxLayout()

        self.path_label = QLabel("No template selected.")
        self.path_label.setStyleSheet("color: #666;")
        row.addWidget(self.path_label, 1)

        self.btn_browse = QPushButton("Select Template (HTML)")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._pick_template)
        row.addWidget(self.btn_browse)

        self.btn_save = QPushButton("Save Result")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_save)

        root.addLayout(row)

        # Preview (rendered snapshot)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 10px; padding: 6px;")
        self.preview.setPlaceholderText("Rendered template preview will appear here.")
        root.addWidget(self.preview, 1)

        hint = QLabel("Placeholders: {{LAB_NAME}}, {{PATIENT_NAME}}, {{TEST_NAME}}, {{DATE}} etc.")
        hint.setStyleSheet("color: #777;")
        root.addWidget(hint)

    def _header_text(self) -> str:
        pid = self.patient_row.get("Patient ID", "-")
        name = self.patient_row.get("Name", "-")
        test = self.request.get("test_name", "Unknown Test")
        rid = self.request.get("request_id", "-")
        return f"Patient: {name} | {pid}\nTest: {test} | Request ID: {rid}"

    def _pick_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select HTML Template",
            "",
            "HTML (*.html *.htm)"
        )
        if not path:
            return

        self.template_path = path
        self.path_label.setText(Path(path).name)

        try:
            raw = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            QMessageBox.warning(self, "Read error", "Could not read the template file.")
            return

        lab = LabProfile.load().__dict__
        ctx = build_context(lab, self.patient_row, self.request)
        self.rendered = render_placeholders(raw, ctx)

        # For Phase-1 preview, show as plain text (avoid HTML rendering surprises)
        self.preview.setPlainText(self.rendered)

    def load_payload(self, payload: dict) -> None:
        self.template_path = payload.get("template_path", "")
        self.rendered = payload.get("rendered", "")
        self.path_label.setText(Path(self.template_path).name if self.template_path else "Template (snapshot)")
        self.preview.setPlainText(self.rendered)

    def _save(self):
        if not self.rendered.strip():
            QMessageBox.information(self, "No content", "Select a template and render it before saving.")
            return

        payload = {
            "type": "pc_template",
            "patient": dict(self.patient_row),
            "request": dict(self.request),
            "template_path": self.template_path,
            "rendered": self.rendered,  # snapshot for history stability
            "status": "draft",
        }
        self.saved.emit(payload)
        QMessageBox.information(self, "Saved", "Template-based result saved to patient profile (draft).")
