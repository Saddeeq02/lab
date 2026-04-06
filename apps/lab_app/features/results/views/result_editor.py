# apps/lab_app/features/results/views/result_editor.py
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ResultEditorView(QWidget):
    """
    L3-2 stub editor.
    L3-3 will expand this for table grid editor.
    """

    def __init__(self, mode: str, patient_row: dict, request: dict):
        super().__init__()
        self.mode = mode
        self.patient_row = patient_row
        self.request = request

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel(f"Result Editor Mode: {mode.upper()}"))
        layout.addWidget(QLabel(f"Test: {request.get('test_name')}"))
        layout.addWidget(QLabel(f"Patient: {patient_row.get('Name')}"))
        layout.addStretch()
