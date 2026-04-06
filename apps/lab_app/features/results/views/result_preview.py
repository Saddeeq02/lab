# apps/lab_app/features/results/views/result_preview.py
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ResultPreviewView(QWidget):
    """
    L3-2 stub for template-based results.
    """

    def __init__(self, patient_row: dict, request: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Template-based Result"))
        layout.addWidget(QLabel(f"Test: {request.get('test_name')}"))
        layout.addWidget(QLabel("Templates will be loaded from PC in L4."))
        layout.addStretch()
