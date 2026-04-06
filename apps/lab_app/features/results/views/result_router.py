# apps/lab_app/features/results/views/result_router.py
from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class ResultRouter(QWidget):
    """
    Internal router for the Patient Profile -> Result tab.
    L3-2: show mode-specific placeholders.
    L3-3: table mode becomes the grid editor.
    """

    def __init__(self):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._current: QWidget | None = None
        self.show_hint("Select a result mode to begin.")

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._current = None

    def show_hint(self, text: str) -> None:
        self._clear()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #666;")
        self._layout.addWidget(lbl)
        self._current = lbl

    def open_table_editor(self, patient_row: dict, request: dict) -> None:
        from apps.lab_app.features.results.views.result_table_editor import ResultTableEditorView

        self._clear()

        editor = ResultTableEditorView(patient_row=patient_row, request=request)
        self._layout.addWidget(editor)
        self._current = editor

    def open_structured_editor(self, patient_row: dict, request: dict) -> None:
        from apps.lab_app.features.results.views.result_structured_editor import StructuredResultEditorView

        self._clear()
        editor = StructuredResultEditorView(patient_row=patient_row, request=request)
        self._layout.addWidget(editor)
        self._current = editor


    def open_written_editor(self, patient_row: dict, request: dict) -> None:
        from apps.lab_app.features.results.views.result_written_editor import WrittenResultEditorView

        self._clear()
        editor = WrittenResultEditorView(patient_row=patient_row, request=request)
        self._layout.addWidget(editor)
        self._current = editor


    def open_pc_template(self, patient_row: dict, request: dict) -> None:
        from apps.lab_app.features.results.views.result_pc_template import PCTemplateResultView
        self._clear()
        editor = PCTemplateResultView(patient_row=patient_row, request=request)
        self._layout.addWidget(editor)
        self._current = editor