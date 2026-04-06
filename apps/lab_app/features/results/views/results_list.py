# apps/lab_app/features/results/views/result_router.py
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from apps.lab_app.features.results.views.result_editor import ResultEditorView
from apps.lab_app.features.results.views.result_preview import ResultPreviewView


class ResultRouter(QWidget):
    """
    Internal router for Result tab.
    Switches editor based on selected mode.
    """

    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._current = None

        self.show_hint("Select a result mode to begin.")

    def clear(self):
        if self._current:
            self._current.setParent(None)
            self._current = None

    def show_hint(self, text: str):
        self.clear()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #666;")
        self._layout.addWidget(lbl)
        self._current = lbl

    def open_table_editor(self, patient_row: dict, request: dict):
        self.clear()
        self._current = ResultEditorView(
            mode="table",
            patient_row=patient_row,
            request=request,
        )
        self._layout.addWidget(self._current)

    def open_writing_editor(self, patient_row: dict, request: dict):
        self.clear()
        self._current = ResultEditorView(
            mode="writing",
            patient_row=patient_row,
            request=request,
        )
        self._layout.addWidget(self._current)

    def open_template_preview(self, patient_row: dict, request: dict):
        self.clear()
        self._current = ResultPreviewView(
            patient_row=patient_row,
            request=request,
        )
        self._layout.addWidget(self._current)
