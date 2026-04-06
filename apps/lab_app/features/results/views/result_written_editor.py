# apps/lab_app/features/results/views/result_written_editor.py
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox
)


class WrittenResultEditorView(QWidget):
    """
    Structured narrative result editor:
    - Findings
    - Interpretation
    - Impression / Conclusion
    - Recommendations
    """
    saved = Signal(dict)

    def __init__(self, patient_row: dict, request: dict):
        super().__init__()
        self.patient_row = patient_row or {}
        self.request = request or {}

        root = QVBoxLayout(self)
        root.setSpacing(10)

        header = QLabel(self._header_text())
        header.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.setStyleSheet(
            "padding: 10px; border: 1px solid #d9d9d9; border-radius: 10px; background: #fafafa; font-weight: 600;"
        )
        root.addWidget(header)

        # Controls
        controls = QHBoxLayout()
        controls.addStretch()
        self.btn_save = QPushButton("Save Result")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save)
        controls.addWidget(self.btn_save)
        root.addLayout(controls)

        # Sections
        self.findings = self._section("Clinical Findings")
        self.interpretation = self._section("Interpretation")
        self.impression = self._section("Impression / Conclusion")
        self.recommendations = self._section("Recommendations (optional)")

        root.addWidget(self.findings["label"])
        root.addWidget(self.findings["edit"], 1)

        root.addWidget(self.interpretation["label"])
        root.addWidget(self.interpretation["edit"], 1)

        root.addWidget(self.impression["label"])
        root.addWidget(self.impression["edit"], 1)

        root.addWidget(self.recommendations["label"])
        root.addWidget(self.recommendations["edit"], 1)

    def _section(self, title: str) -> dict:
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: 800;")

        ed = QTextEdit()
        ed.setPlaceholderText(f"Enter {title.lower()}...")
        ed.setStyleSheet("border: 1px solid #d9d9d9; border-radius: 10px; padding: 6px;")
        ed.setAcceptRichText(False)  # keep clean text; PDF-friendly
        return {"label": lbl, "edit": ed}

    def _header_text(self) -> str:
        pid = self.patient_row.get("Patient ID", "-")
        name = self.patient_row.get("Name", "-")
        sex = self.patient_row.get("Sex", "-")
        age = self.patient_row.get("Age", "-")
        test = self.request.get("test_name", "Unknown Test")
        rid = self.request.get("request_id", "-")
        return f"Patient: {name} | {pid} | {sex} | {age}\nTest: {test} | Request ID: {rid}"

    def load_payload(self, payload: dict) -> None:
        data = payload.get("text", {})
        self.findings["edit"].setPlainText(data.get("findings", ""))
        self.interpretation["edit"].setPlainText(data.get("interpretation", ""))
        self.impression["edit"].setPlainText(data.get("impression", ""))
        self.recommendations["edit"].setPlainText(data.get("recommendations", ""))

    def _save(self) -> None:
        text = {
            "findings": self.findings["edit"].toPlainText().strip(),
            "interpretation": self.interpretation["edit"].toPlainText().strip(),
            "impression": self.impression["edit"].toPlainText().strip(),
            "recommendations": self.recommendations["edit"].toPlainText().strip(),
        }

        if not any(text.values()):
            QMessageBox.information(self, "Nothing to save", "Please write at least one section before saving.")
            return

        payload = {
            "type": "written",
            "patient": dict(self.patient_row),
            "request": dict(self.request),
            "text": text,
            "status": "draft",
        }
        self.saved.emit(payload)
        QMessageBox.information(self, "Saved", "Written result saved to patient profile (draft).")
