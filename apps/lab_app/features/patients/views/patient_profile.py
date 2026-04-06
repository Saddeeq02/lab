# apps/lab_app/features/patients/views/patient_profile.py
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFrame, QMessageBox
)
from PySide6.QtCore import QThread, QObject, Signal
from shared.config.backend_profile import BackendProfile
from shared.net.api_client import ApiClient, ApiConfig, ApiError

from shared.uix.widgets.tables import DataTable
from PySide6.QtWidgets import QComboBox
from apps.lab_app.features.results.views.result_router import ResultRouter
from PySide6.QtWidgets import QFileDialog
from shared.config.lab_profile import LabProfile
from apps.lab_app.features.results.services.pdf_service import generate_bundle_pdf
from apps.lab_app.features.results.services.docx_service import generate_bundle_docx

import tempfile
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QPainter, QPageSize, QImage

import os
from PySide6.QtWidgets import QAbstractItemView

from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout,
    QVBoxLayout, QWidget, QMessageBox, QDialog, QLabel
)

class _PatientHydrateWorker(QObject):
    finished = Signal(dict)   # {"patient": {...}, "results": [...], "test_types": {...}}
    failed = Signal(str)

    def __init__(self, base_url: str, timeout_s: float, patient_id: int):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.patient_id = patient_id

    def run(self):
        try:
            api = ApiClient(ApiConfig(base_url=self.base_url, timeout_s=self.timeout_s))

            patient = api.get_json(f"/api/patients/{self.patient_id}")

            # Results list (your backend supports list endpoint in router)
            # GET /api/results?patient_id=...&limit=...
            results_data = api.get_json("/api/results", params={"patient_id": self.patient_id, "limit": 200, "offset": 0})

            # Results response may be {"value":[...], "Count": n} OR a plain list
            if isinstance(results_data, dict):
                results = results_data.get("value", [])
            elif isinstance(results_data, list):
                results = results_data
            else:
                results = []

            # Test types name map (optional, but makes results readable)
            tt_data = api.get_json("/api/test-types")
            if isinstance(tt_data, dict):
                tt_list = tt_data.get("value", [])
            elif isinstance(tt_data, list):
                tt_list = tt_data
            else:
                tt_list = []

            test_types = {}
            for t in tt_list:
                tid = t.get("id")
                name = t.get("name") or f"TestType #{tid}"
                if tid is not None:
                    test_types[int(tid)] = name

            self.finished.emit({"patient": patient, "results": results, "test_types": test_types})

        except ApiError as e:
            extra = ""
            if e.payload is not None:
                extra = f"\n\nDetails: {e.payload}"
            self.failed.emit(f"{str(e)}{extra}")
        except Exception as e:
            self.failed.emit(str(e))


class _ResultDetailWorker(QObject):
    finished = Signal(dict)   # result detail
    failed = Signal(str)

    def __init__(self, base_url: str, timeout_s: float, result_id: int):
        super().__init__()
        self.base_url = base_url
        self.timeout_s = timeout_s
        self.result_id = result_id

    def run(self):
        try:
            api = ApiClient(ApiConfig(base_url=self.base_url, timeout_s=self.timeout_s))
            r = api.get_json(f"/api/results/{self.result_id}")
            self.finished.emit(r)
        except ApiError as e:
            extra = ""
            if e.payload is not None:
                extra = f"\n\nDetails: {e.payload}"
            self.failed.emit(f"{str(e)}{extra}")
        except Exception as e:
            self.failed.emit(str(e))




class PatientProfileView(QWidget):
    """
    L3-1:
    - Requested Tests tab has a real table
    - Approve -> jumps to Result tab
    - Reject -> removes request locally (stub for receptionist notification)
    """

    def __init__(self, patient_row: dict | None = None):
        super().__init__()
        self.patient_row = patient_row or {}
        self.patient_id = self.patient_row.get("id")
        self._bp = BackendProfile.load()
        self._thread: QThread | None = None
        self._worker: QObject | None = None

        # Auto-load backend on open (Option A)
        self._load_backend_data()


        # Mock requested tests (UIX-only for now)
        # Requested tests (now backend-driven)
        self._requests = []
        self._load_test_requests_from_backend()


        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Top header row
        top = QHBoxLayout()
        title = QLabel("Patient Profile")
        title.setStyleSheet("font-size: 14px; font-weight: 800;")
        top.addWidget(title)

        top.addStretch()
        self._saved_results: list[dict] = []
        self._history_lines: list[str] = []
        
        # Result bundle (L3-A)
        self._bundle_requests: list[dict] = []   # approved tests in bundle
        self._bundle_results: dict[str, dict] = {}  # request_id -> saved result payload


        self.btn_back = QPushButton("Back to Profiles")
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._go_back)
        top.addWidget(self.btn_back)
        root.addLayout(top)

        # Patient summary strip
        self.summary_label = QLabel(self._summary_text())
        self.summary_label.setStyleSheet("color: #444;")
        root.addWidget(self.summary_label)

        
        # Results history (system-of-record, in-memory for now)
        self._result_history: list[dict] = []     # list of history events
        self._history_payloads: dict[str, dict] = {}  # event_id -> payload snapshot
        self._reopen_payload: dict | None = None


        # Tabs (store reference so we can switch on approve)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_biodata(), "Biodata")
        self.tabs.addTab(self._tab_requested_tests(), "Requested Tests")
        self.tabs.addTab(self._tab_results(), "Result")
        self.tabs.addTab(self._tab_backend_results(), "Backend Results")

        self.tabs.addTab(self._tab_history(), "Results History")
        
        root.addWidget(self.tabs, 1)
        
        
        

    # ---------------------------
    # Header helpers
    # ---------------------------
    def _summary_text(self) -> str:
        pid = self.patient_row.get("Patient ID", "-")
        name = self.patient_row.get("Name", "-")
        sex = self.patient_row.get("Sex", "-")
        age = self.patient_row.get("Age", "-")
        return f"{name}  |  {pid}  |  {sex}  |  {age}"

    # ---------------------------
    # Tabs
    # ---------------------------
    def _tab_biodata(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.addWidget(QLabel("Full Bio data and modification are available in Cashier or receptionist App."))
        l.addWidget(QLabel("This tab will be read-only for Lab staff."))
        l.addStretch()
        return w

    def _tab_requested_tests(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)

        # Top actions bar
        bar = QHBoxLayout()

        info = QLabel("Requested tests submitted by receptionist. Select a request to Approve or Reject.")
        info.setStyleSheet("color: #666;")
        bar.addWidget(info)
        bar.addStretch()

        self.btn_approve = QPushButton("Approve and proceed")

        self.btn_approve.setCursor(Qt.PointingHandCursor)
        self.btn_approve.clicked.connect(self._approve_selected_request)
        bar.addWidget(self.btn_approve)

        self.btn_reject = QPushButton("Reject")
        self.btn_reject.setCursor(Qt.PointingHandCursor)
        self.btn_reject.clicked.connect(self._reject_selected_request)
        bar.addWidget(self.btn_reject)

        l.addLayout(bar)

        # Table
        cols = ["Request ID", "Test Name", "Requested By", "Requested At", "Status"]
        self.requests_table = DataTable(columns=cols)
        self.requests_table.set_rows(self._requests_to_rows())
        l.addWidget(self.requests_table, 1)

        # Footer note
        note = QLabel("Approve moves the request to Result preparation tab automatically. Reject removes it and notifies receptionist (stub).")
        note.setStyleSheet("color: #888;")
        l.addWidget(note)

        return w

    def _tab_results(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)

        # Bundle summary
        self.bundle_label = QLabel("Result Bundle: 0 test(s)")
        self.bundle_label.setStyleSheet("font-weight: 700;")
        l.addWidget(self.bundle_label)

        self.bundle_list = QLabel("No tests added yet.")
        self.bundle_list.setStyleSheet("color: #555;")
        self.bundle_list.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.addWidget(self.bundle_list)
        
        # Hint label (used by approve flow)
        self.result_hint = QLabel("Approve a requested test to prepare a result.")
        self.result_hint.setStyleSheet("color: #666;")
        l.addWidget(self.result_hint)


        # Active request
        self.active_request_label = QLabel("Active Request: None")
        self.active_request_label.setStyleSheet("font-weight: 700;")
        l.addWidget(self.active_request_label)

        # Mode selector
        self.mode_selector = QComboBox()
        self.mode_selector.addItem("Select result mode...")
        self.mode_selector.addItem("Table format")        # existing grid editor
        self.mode_selector.addItem("Structured Table")    # NEW (auto-flagging)
        self.mode_selector.addItem("Writing format")
        self.mode_selector.addItem("Template (PC)")
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        # REPLACED: Single Professional Print Action
        self.btn_direct_print = QPushButton("Direct Print Report")
        self.btn_direct_print.setProperty("variant", "primary") # Deep Blue Blue-Black
        self.btn_direct_print.setCursor(Qt.PointingHandCursor)
        self.btn_direct_print.clicked.connect(self._print_bundle_direct)
        btn_row.addWidget(self.btn_direct_print)

        l.addLayout(btn_row)



        self.mode_selector.currentIndexChanged.connect(self._on_mode_changed)
        l.addWidget(self.mode_selector)

        # Router
        self.result_router = ResultRouter()
        l.addWidget(self.result_router, 1)

        return w


    def _on_mode_changed(self, idx: int):
        w = None  # IMPORTANT: always define w

        if idx == 0:
            self.result_router.show_hint("Select a result mode to begin.")
            return

        if not hasattr(self, "_active_request") or self._active_request is None:
            self.result_router.show_hint("No approved request selected.")
            self.mode_selector.setCurrentIndex(0)
            return

        if idx == 1:
            self.result_router.open_table_editor(self.patient_row, self._active_request)
            w = getattr(self.result_router, "_current", None)
            if w is not None and hasattr(w, "saved"):
                w.saved.connect(self._on_result_saved)

        elif idx == 2:
            self.result_router.open_structured_editor(self.patient_row, self._active_request)
            w = getattr(self.result_router, "_current", None)
            if w is not None and hasattr(w, "saved"):
                w.saved.connect(self._on_result_saved)

        elif idx == 3:
            self.result_router.open_written_editor(self.patient_row, self._active_request)
            w = getattr(self.result_router, "_current", None)
            if w is not None and hasattr(w, "saved"):
                w.saved.connect(self._on_result_saved)

        elif idx == 4:
            self.result_router.open_pc_template(self.patient_row, self._active_request)
            w = getattr(self.result_router, "_current", None)
            if w is not None and hasattr(w, "saved"):
                w.saved.connect(self._on_result_saved)

        # Prefill ONLY after w has been created
        if self._reopen_payload is not None and w is not None:
            rp = self._reopen_payload
            if rp.get("request", {}).get("request_id") == self._active_request.get("request_id"):
                if hasattr(w, "load_payload"):
                    w.load_payload(rp)
                self._reopen_payload = None

            
            
    def _on_result_saved(self, payload: dict) -> None:
        rid = payload.get("request", {}).get("request_id")
        if not rid:
            return

        backend_id = None
        if hasattr(self, "_active_request") and self._active_request:
            backend_id = self._active_request.get("backend_result_id")

        ptype = (payload.get("type") or "").strip().lower()

        # ------------------------------------------------------------
        # Persist to backend (UIX-first contract) for structured + table
        # ------------------------------------------------------------
        if ptype in {"structured", "table"}:
            try:
                uix = payload.get("uix") or {}
                snap = uix.get("template_snapshot") or {}
                vals = uix.get("values") or {}
                notes = payload.get("notes")

                # test_type_id must exist (prefer payload.uix, fallback to active request)
                test_type_id = uix.get("test_type_id")
                if not test_type_id and hasattr(self, "_active_request") and self._active_request:
                    test_type_id = self._active_request.get("test_type_id")

                if not test_type_id:
                    QMessageBox.warning(self, "Missing test_type_id", "Save requires test_type_id to persist to backend.")
                    return

                # If no backend result bound yet -> create from snapshot (UIX-first)
                if not backend_id:
                    created = self._backend_instantiate_from_snapshot(
                        int(test_type_id),
                        snap,
                        vals,
                        notes=notes,
                    )
                    new_id = created.get("id")
                    if not new_id:
                        raise RuntimeError("Backend did not return result id.")

                    # bind to request (so future saves PATCH the same result)
                    if hasattr(self, "_active_request") and self._active_request:
                        self._active_request["backend_result_id"] = int(new_id)
                        self._active_request["backend_status"] = created.get("status")
                        backend_id = int(new_id)

                else:
                    # If backend result exists, ensure snapshot compatibility.
                    # If mismatch, create a new UIX-first backend result and rebind (prevents partial/old-shape issues).
                    api = self._backend_api()
                    existing = api.get_json(f"/api/results/{int(backend_id)}")

                    ex_snap = existing.get("template_snapshot") or {}
                    ex_kind = (ex_snap.get("kind") or "").strip().lower()
                    uix_kind = (snap.get("kind") or "").strip().lower()

                    mismatch = False

                    # kind mismatch (e.g., old "table" vs new "grid")
                    if ex_kind and uix_kind and ex_kind != uix_kind:
                        mismatch = True

                    # structured/table(kind="table") row-count mismatch
                    if (not mismatch) and uix_kind == "table" and ex_kind == "table":
                        ex_fields = ex_snap.get("fields") or []
                        uix_fields = snap.get("fields") or []
                        if len(ex_fields) != len(uix_fields):
                            mismatch = True

                    # grid(kind="grid") shape mismatch
                    if (not mismatch) and uix_kind == "grid" and ex_kind == "grid":
                        ex_g = ex_snap.get("grid") or {}
                        uix_g = snap.get("grid") or {}
                        ex_rows = int(ex_g.get("rows", 0) or 0)
                        ex_cols = int(ex_g.get("cols", 0) or 0)
                        uix_rows = int(uix_g.get("rows", 0) or 0)
                        uix_cols = int(uix_g.get("cols", 0) or 0)
                        if ex_rows != uix_rows or ex_cols != uix_cols:
                            mismatch = True

                    if mismatch:
                        created = self._backend_instantiate_from_snapshot(
                            int(test_type_id),
                            snap,
                            vals,
                            notes=notes,
                        )
                        new_id = created.get("id")
                        if not new_id:
                            raise RuntimeError("Backend did not return result id.")

                        if hasattr(self, "_active_request") and self._active_request:
                            self._active_request["backend_result_id"] = int(new_id)
                            self._active_request["backend_status"] = created.get("status")
                            backend_id = int(new_id)
                    else:
                        # Safe to PATCH values normally (snapshot already aligned)
                        self._backend_update_values(int(backend_id), vals, notes=notes)

                # Refresh backend tab list (your existing loader)
                if hasattr(self, "_load_backend_data"):
                    self._load_backend_data()
                    self._load_test_requests_from_backend()


            except Exception as e:
                QMessageBox.warning(self, "Backend Save Failed", f"Could not persist result to backend.\n\n{e}")
                return

        # ---------------------------
        # Local bundle + history flow
        # ---------------------------
        self._bundle_results[rid] = payload
        self._append_history_event(payload, status="completed")

        # Remove the completed request from the front of the queue
        if self._bundle_requests and self._bundle_requests[0]["request_id"] == rid:
            completed = self._bundle_requests.pop(0)
        else:
            self._bundle_requests = [r for r in self._bundle_requests if r["request_id"] != rid]
            completed = payload.get("request") or {}

        # History line sizing
        test_name = completed.get("test_name", "Unknown Test")
        rows = 0
        cols = 0

        if ptype == "table":
            # Prefer UIX snapshot (canonical). Fallback to legacy grid.
            uix = payload.get("uix") or {}
            snap = uix.get("template_snapshot") or {}
            if (snap.get("kind") or "").lower().strip() == "grid":
                g = snap.get("grid") or {}
                rows = int(g.get("rows", 0) or 0)
                cols = int(g.get("cols", 0) or 0)
            else:
                grid = payload.get("grid", {}) or {}
                rows = int(grid.get("rows", 0) or 0)
                cols = int(grid.get("cols", 0) or 0)

        elif ptype == "structured":
            uix = payload.get("uix") or {}
            snap = uix.get("template_snapshot") or {}
            rows = len((snap.get("fields") or []))
            cols = 5  # Parameter/Result/Unit/Ref/Flag

        self._history_lines.append(f"{test_name} ({rid}) - {rows}x{cols} - completed")

        # Advance to next request automatically
        if self._bundle_requests:
            next_req = self._bundle_requests[0]
            self._active_request = next_req

            self.active_request_label.setText(
                f"Active Request: {next_req.get('test_name', 'Unknown Test')}  ({next_req.get('request_id', '-')})"
            )
            if hasattr(self, "result_hint"):
                self.result_hint.setText("Proceed with the next test in the bundle.")

            # Reset result mode selector + router
            self.mode_selector.setCurrentIndex(0)
            self.result_router.show_hint("Select a result mode for the next test.")
        else:
            # Bundle finished
            self._active_request = None
            self.active_request_label.setText("Active Request: None")
            if hasattr(self, "result_hint"):
                self.result_hint.setText("All tests in this bundle are completed.")
            self.mode_selector.setCurrentIndex(0)
            self.result_router.show_hint("Bundle completed. You may review history or print.")

        self._refresh_bundle_ui()

        if hasattr(self, "history_label"):
            self.history_label.setText("\n".join(self._history_lines))


    def _tab_history(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)

        title = QLabel("Results History")
        title.setStyleSheet("font-weight: 800;")
        l.addWidget(title)

        hint = QLabel("View, reprint, or reopen results. Reopen creates a new revision (non-destructive).")
        hint.setStyleSheet("color: #666;")
        l.addWidget(hint)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            ["Time", "Test", "Type", "Status", "Rev", "Request ID"]
        )
        
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        l.addWidget(self.history_table, 1)

        btns = QHBoxLayout()
        btns.addStretch()

        self.btn_view_hist = QPushButton("View")
        self.btn_view_hist.setCursor(Qt.PointingHandCursor)
        self.btn_view_hist.clicked.connect(self._history_view_selected)
        btns.addWidget(self.btn_view_hist)

        self.btn_reprint_hist = QPushButton("Reprint PDF")
        self.btn_reprint_hist.setCursor(Qt.PointingHandCursor)
        self.btn_reprint_hist.clicked.connect(self._history_reprint_selected)
        btns.addWidget(self.btn_reprint_hist)

        self.btn_reopen_hist = QPushButton("Reopen (New Revision)")
        self.btn_reopen_hist.setCursor(Qt.PointingHandCursor)
        self.btn_reopen_hist.clicked.connect(self._history_reopen_selected)
        btns.addWidget(self.btn_reopen_hist)

        l.addLayout(btns)

        self._refresh_history_table()
        return w
    
    def _tab_backend_results(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)

        title = QLabel("Backend Results (Read-only)")
        title.setStyleSheet("font-weight: 800;")
        l.addWidget(title)

        hint = QLabel("This tab shows results stored in the backend system-of-record.")
        hint.setStyleSheet("color: #666;")
        l.addWidget(hint)

        bar = QHBoxLayout()
        bar.addStretch()

        self.btn_backend_refresh = QPushButton("Refresh Backend Results")
        self.btn_backend_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_backend_refresh.clicked.connect(self._load_backend_data)
        bar.addWidget(self.btn_backend_refresh)

        l.addLayout(bar)

        cols = ["Result ID", "Test", "Status", "Created At", "Updated At"]
        self.backend_results_table = DataTable(columns=cols)
        self.backend_results_table.itemDoubleClicked.connect(
        self._open_backend_result
    )

        self.backend_results_table.row_activated.connect(self._backend_open_selected)
        l.addWidget(self.backend_results_table, 1)

        self.backend_status = QLabel("Not loaded")
        self.backend_status.setStyleSheet("color: #666;")
        l.addWidget(self.backend_status)

        return w

    def _open_backend_result(self, item):
        row = item.row()
        result_id_item = self.backend_results_table.item(row, 0)
        if not result_id_item:
            return

        result_id = int(result_id_item.text())

        from shared.net.api_client import ApiClient, ApiConfig, ApiError
        from apps.lab_app.features.results.views.backend_result_viewer import (
            BackendResultViewerDialog
        )

        bp = BackendProfile.load()
        api = ApiClient(ApiConfig(
            base_url=bp.base_url,
            timeout_s=bp.timeout_s,
        ))

        dlg = BackendResultViewerDialog(result_id, api, self)
        dlg.exec()


    def _append_history_event(self, payload: dict, status: str = "completed") -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rid = payload.get("request", {}).get("request_id", "-")
        test = payload.get("request", {}).get("test_name", "Unknown Test")
        rtype = payload.get("type", "unknown")

        # revision per request_id
        prev = [e for e in self._result_history if e.get("request_id") == rid]
        rev = (max([e.get("revision", 0) for e in prev]) + 1) if prev else 1

        event_id = f"{rid}-rev{rev}-{len(self._result_history)+1}"

        event = {
            "event_id": event_id,
            "time": now,
            "test": test,
            "type": rtype,
            "status": status,
            "revision": rev,
            "request_id": rid,
        }

        self._result_history.insert(0, event)  # newest on top
        self._history_payloads[event_id] = payload
        self._refresh_history_table()

    
    def _refresh_bundle_ui(self) -> None:
        count = len(self._bundle_requests)
        self.bundle_label.setText(f"Result Bundle: {count} pending test(s)")

        if count == 0:
            self.bundle_list.setText("All tests completed.")
            return

        lines = []
        for i, r in enumerate(self._bundle_requests):
            rid = r.get("request_id")
            name = r.get("test_name")
            prefix = "▶ " if i == 0 else "  "
            lines.append(f"{prefix}{name} ({rid})")

        self.bundle_list.setText("\n".join(lines))
        
        
    def _refresh_history_table(self) -> None:
        if not hasattr(self, "history_table"):
            return

        self.history_table.setRowCount(len(self._result_history))

        for i, e in enumerate(self._result_history):
            self.history_table.setItem(i, 0, QTableWidgetItem(e.get("time", "")))
            self.history_table.setItem(i, 1, QTableWidgetItem(e.get("test", "")))
            self.history_table.setItem(i, 2, QTableWidgetItem(e.get("type", "")))
            self.history_table.setItem(i, 3, QTableWidgetItem(e.get("status", "")))
            self.history_table.setItem(i, 4, QTableWidgetItem(str(e.get("revision", ""))))
            self.history_table.setItem(i, 5, QTableWidgetItem(e.get("request_id", "")))

        self.history_table.resizeColumnsToContents()

    def _history_selected_event(self) -> dict | None:
        if not hasattr(self, "history_table"):
            return None
        row = self.history_table.currentRow()
        if row < 0 or row >= len(self._result_history):
            return None
        
        return self._result_history[row]
    
    def _history_view_selected(self) -> None:
        e = self._history_selected_event()
        if not e:
            QMessageBox.information(self, "No selection", "Select a history entry first.")
            return

        raw_payload = self._history_payloads.get(e["event_id"])
        if not raw_payload:
            return

        # --- STEP 1.2 FIX: Normalize if it's from backend ---
        if "template_snapshot" in raw_payload:
            payload = self._normalize_backend_payload(raw_payload)
        else:
            payload = raw_payload

        dlg = QDialog(self)
        dlg.setWindowTitle("Result Preview")
        dlg.resize(900, 520)
        # ... (rest of your existing QDialog code remains the same)

        root = QVBoxLayout(dlg)
        root.setSpacing(10)

        root.addWidget(QLabel(f"{e['test']}  |  {e['type']}  |  Rev {e['revision']}  |  {e['time']}"))

        # Render based on type
        typ = payload.get("type")
        if typ == "structured":
            from apps.lab_app.features.results.views.result_structured_editor import StructuredResultEditorView
            v = StructuredResultEditorView(self.patient_row, payload.get("request", {}))
            v.load_payload(payload)
            v.btn_save.setVisible(False)  # read-only preview feel
            root.addWidget(v, 1)

        elif typ == "table":
            from apps.lab_app.features.results.views.result_table_editor import ResultTableEditorView
            v = ResultTableEditorView(self.patient_row, payload.get("request", {}))
            v.load_payload(payload)
            v.btn_save.setVisible(False)
            v.btn_clear.setVisible(False)
            root.addWidget(v, 1)
            
        elif typ == "pc_template":
            from apps.lab_app.features.results.views.result_pc_template import PCTemplateResultView
            v = PCTemplateResultView(self.patient_row, payload.get("request", {}))
            v.load_payload(payload)
            v.btn_save.setVisible(False)
            v.btn_browse.setVisible(False)
            root.addWidget(v, 1)


        else:
            root.addWidget(QLabel("Unsupported result type for preview."))

        dlg.exec()


    def _history_reprint_selected(self) -> None:
        e = self._history_selected_event()
        if not e:
            QMessageBox.information(self, "No selection", "Select a history entry first.")
            return
        # Inside _history_reopen_selected or _history_reprint_selected
        raw_payload = self._history_payloads.get(e["event_id"])
        if not raw_payload: return

        # Use normalized version
        payload = self._normalize_backend_payload(raw_payload) if "template_snapshot" in raw_payload else raw_payload

        # ... proceed with logic
        payload = self._history_payloads.get(e["event_id"])
        if not payload:
            return

        from PySide6.QtWidgets import QFileDialog

        profile = LabProfile.load()
        pid = self.patient_row.get("Patient ID", "patient")
        rid = e.get("request_id", "result")
        default_name = f"{pid}_{rid}_report.pdf"

        path, _ = QFileDialog.getSaveFileName(self, "Reprint Result PDF", default_name, "PDF (*.pdf)")
        if not path:
            return

        out = generate_bundle_pdf(
            output_path=path,
            lab_profile=profile.__dict__,
            patient_row=self.patient_row,
            bundle_results={rid: payload},  # single-test report
        )

        try:
            os.startfile(out)  # Windows open
        except Exception:
            pass
        
    def _history_reopen_selected(self) -> None:
        e = self._history_selected_event()
        if not e:
            QMessageBox.information(self, "No selection", "Select a history entry first.")
            return
        # Inside _history_reopen_selected or _history_reprint_selected
        raw_payload = self._history_payloads.get(e["event_id"])
        if not raw_payload: return

        # Use normalized version
        payload = self._normalize_backend_payload(raw_payload) if "template_snapshot" in raw_payload else raw_payload

        # ... proceed with logic
        payload = self._history_payloads.get(e["event_id"])
        if not payload:
            return

        # Set active request and mark reopen payload
        self._active_request = payload.get("request", {})
        self._reopen_payload = payload

        # Go to Result tab
        self.tabs.setCurrentIndex(2)
        self.active_request_label.setText(
            f"Active Request: {self._active_request.get('test_name')}  ({self._active_request.get('request_id')})"
        )
        if hasattr(self, "result_hint"):
            self.result_hint.setText("Reopened from history. Edit and save to create a new revision.")

        # Auto-select mode based on payload type
        typ = payload.get("type")
        if typ == "structured":
            # Structured Table index (based on your current selector order)
            self.mode_selector.setCurrentIndex(2)
        elif typ == "table":
            self.mode_selector.setCurrentIndex(1)
        else:
            self.mode_selector.setCurrentIndex(0)





    # ---------------------------
    # Requested Tests actions
    # ---------------------------
    def _selected_request(self) -> dict | None:
        row = self.requests_table.selected_row_data() if hasattr(self, "requests_table") else None
        if not row:
            return None
        # map back to internal request by Request ID
        rid = row.get("Request ID")
        for req in self._requests:
            if req["request_id"] == rid:
                return req
        return None

    def _approve_selected_request(self) -> None:
        req = self._selected_request()
        if not req:
            QMessageBox.information(self, "No selection", "Please select a requested test first.")
            return

        # Avoid duplicates in bundle queue
        if any(r.get("request_id") == req.get("request_id") for r in self._bundle_requests):
            QMessageBox.information(self, "Already added", "This test is already in the result bundle.")
            return
        # Backend: accept request (authoritative)
        try:
            self._backend_update_test_request_status(int(req["request_id"]), "accepted")
        except Exception as e:
            QMessageBox.warning(self, "Approve Failed", f"Could not accept request in backend.\n\n{e}")
            return

        # Mark approved locally
        req["status"] = "accepted"

        # Resolve backend ids for later use (but DO NOT create any backend row here)
        try:
            test_type_id, template_id = self._resolve_backend_ids_for_request(req)
            req["test_type_id"] = int(test_type_id) if test_type_id is not None else None

            # Keep template_id only as provenance/mapping; UIX-first structured may not use it
            req["template_id"] = int(template_id) if template_id is not None else None

            # IMPORTANT: do not instantiate in backend here
            # We only bind backend_result_id when user saves the result
            req.setdefault("backend_result_id", None)
            req.setdefault("backend_status", None)

        except Exception as e:
            QMessageBox.warning(
                self,
                "Backend Mapping Failed",
                f"Could not resolve backend ids for this request.\n\n{e}"
            )
            return

        # Enqueue (bundle queue)
        self._bundle_requests.append(req)
        self.requests_table.set_rows(self._requests_to_rows())
        # Remove from pending list UI (since backend moved it out of pending)
        self._requests = [r for r in self._requests if r["request_id"] != req["request_id"]]
        self.requests_table.set_rows(self._requests_to_rows())


        # Only set active when this is the FIRST item (start of queue)
        if len(self._bundle_requests) == 1:
            self._active_request = self._bundle_requests[0]

            # No backend id at approve-time anymore
            self.active_request_label.setText(
                f"Active Request: {req.get('test_name')}  ({req.get('request_id')})"
            )

            if hasattr(self, "result_hint"):
                self.result_hint.setText("Choose a result mode for the active test.")

            # Jump to Result tab
            self.tabs.setCurrentIndex(2)

        self._refresh_bundle_ui()

    def _reject_selected_request(self) -> None:
        req = self._selected_request()
        if not req:
            QMessageBox.information(self, "No selection", "Please select a requested test first.")
            return

        # Confirm reject (UIX-first; later replace with shared dialog if desired)
        res = QMessageBox.question(
            self,
            "Reject Request",
            f"Reject '{req['test_name']}'?\n\nThis will remove the request and notify receptionist.",
            QMessageBox.Yes | QMessageBox.No
        )
        if res != QMessageBox.Yes:
            return
        
        try:
            self._backend_update_test_request_status(int(req["request_id"]), "rejected")
        except Exception as e:
            QMessageBox.warning(self, "Reject Failed", f"Could not reject request in backend.\n\n{e}")
            return


        # Remove locally
        self._requests = [r for r in self._requests if r["request_id"] != req["request_id"]]
        self.requests_table.set_rows(self._requests_to_rows())

        # Stub notification
        QMessageBox.information(self, "Rejected", "Request rejected. Receptionist notification will be wired in L5.")

    # ---------------------------
    # Back navigation (safe)
    # ---------------------------
    def _go_back(self):
        from apps.lab_app.features.patients.views.patients_list import PatientsListView

        parent = self.parentWidget()
        if parent is None:
            return

        layout = parent.layout()
        if layout is None:
            return

        idx = -1
        for i in range(layout.count()):
            if layout.itemAt(i).widget() is self:
                idx = i
                break

        if idx >= 0:
            def do_swap():
                self.setParent(None)
                layout.insertWidget(idx, PatientsListView())

            QTimer.singleShot(0, do_swap)

    # ---------------------------
    # Mock data (UIX only)
    # ---------------------------
    def _mock_requests(self) -> list[dict]:
        # In real L4/L5 this comes from test_requests VM/API linked to receptionist app.
        return [
            {
                "request_id": "R-1001",
                "test_name": "Full Blood Count (FBC)",
                "requested_by": "Reception",
                "requested_at": "2026-01-19 09:12",
                "status": "pending",
            },
            {
                "request_id": "R-1002",
                "test_name": "Widal Test",
                "requested_by": "Reception",
                "requested_at": "2026-01-19 09:14",
                "status": "pending",
            },
        ]

    def _requests_to_rows(self) -> list[dict]:
        rows = []
        for r in self._requests:
            rows.append({
                "Request ID": r["request_id"],
                "Test Name": r["test_name"],
                "Requested By": r["requested_by"],
                "Requested At": r["requested_at"],
                "Status": r["status"],
            })
        return rows



    def _print_bundle_direct(self):
        """
        Triggers the PDF engine and sends output directly to the printer 
        without saving a permanent file to the drive.
        """
        # 1. Validation: Ensure we have something to print
        if not hasattr(self, "_bundle_results") or not self._bundle_results:
            QMessageBox.information(self, "Clinical Alert", "No saved results found in the bundle to print.")
            return

        # 2. Setup the Clinical Printer
        # HighResolution ensures the lab logos and table lines stay sharp
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        
        # Identify the document in the printer queue
        pid = self.patient_row.get('Patient ID', 'Unknown')
        printer.setDocName(f"LabReport_{pid}")

        # 3. Show System Print Dialog
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.Accepted:
            return

        # 4. Generate the 'Invisible' PDF
        from apps.lab_app.features.results.services.pdf_service import generate_bundle_pdf
        from shared.config.lab_profile import LabProfile

        profile = LabProfile.load()
        
        # Create a temporary file to hold the generated PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        # Initialize painter outside try to ensure safe cleanup
        painter = QPainter()

        try:
            # Generate the PDF using your engine
            generate_bundle_pdf(
                output_path=tmp_path,
                lab_profile=profile.__dict__,
                patient_row=self.patient_row,
                bundle_results=self._bundle_results,
            )

            # 5. Paint PDF Pages to the Printer
            pdf_doc = QPdfDocument()
            pdf_doc.load(tmp_path)
            
            # Explicitly begin painting on the printer
            if not painter.begin(printer):
                raise Exception("Could not initialize printer canvas.")
                
            for i in range(pdf_doc.pageCount()):
                if i > 0:
                    printer.newPage()
                
                # Get physical pixel size of the printer page for high-res rendering
                page_rect = printer.pageRect(QPrinter.DevicePixel)
                page_size = page_rect.size().toSize()
                
                # Render PDF page to high-res QImage (required for PySide6 signature)
                img = pdf_doc.render(i, page_size)
                
                # Draw the image starting at the top-left (0,0)
                painter.drawImage(0, 0, img)
                
            # Crucial: Explicitly end painting to release the printer device
            painter.end()

        except Exception as e:
            # Safety: If painting fails, ensure the device is released to avoid crashes
            if painter.isActive():
                painter.end()
            QMessageBox.critical(self, "Printing Failed", f"Could not communicate with printer: {str(e)}")
            
        finally:
            # 6. Cleanup: Remove the trace from the disk immediately
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass



    def _export_bundle_pdf(self):
        if not hasattr(self, "_bundle_results") or not self._bundle_results:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Nothing to export", "No saved results found in the bundle yet.")
            return

        profile = LabProfile.load()
        default_name = f"{self.patient_row.get('Patient ID','patient')}_bundle_report.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Bundle PDF",
            default_name,
            "PDF (*.pdf)"
        )
        if not path:
            return

        out = generate_bundle_pdf(
            output_path=path,
            lab_profile=profile.__dict__,
            patient_row=self.patient_row,
            bundle_results=self._bundle_results,
        )

        # Open PDF on Windows
        try:
            os.startfile(out)  # type: ignore[attr-defined]
        except Exception:
            pass


    def _load_backend_data(self):
        # Only if enabled and patient_id available
        bp = BackendProfile.load()
        self._bp = bp

        if not bp.enabled:
            if hasattr(self, "backend_status"):
                self.backend_status.setText("Backend integration is disabled in Settings.")
            return

        if not self.patient_id:
            if hasattr(self, "backend_status"):
                self.backend_status.setText("No backend patient id found for this profile.")
            return

        if hasattr(self, "btn_backend_refresh"):
            self.btn_backend_refresh.setEnabled(False)
        if hasattr(self, "backend_status"):
            self.backend_status.setText("Loading from backend...")

        # teardown existing thread
        if self._thread is not None:
            try:
                self._thread.quit()
                self._thread.wait(200)
            except Exception:
                pass
            self._thread = None
            self._worker = None

        self._thread = QThread()
        self._worker = _PatientHydrateWorker(
            base_url=bp.base_url,
            timeout_s=bp.timeout_s,
            patient_id=int(self.patient_id),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_backend_loaded)
        self._worker.failed.connect(self._on_backend_failed)

        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._on_backend_done)

        self._thread.start()


    def _on_backend_loaded(self, data: dict):
        patient = data.get("patient", {}) or {}
        results = data.get("results", []) or []
        test_types = data.get("test_types", {}) or {}

        # 1. Update patient header / summary (Existing Logic)
        self.patient_row["Patient ID"] = patient.get("patient_no", self.patient_row.get("Patient ID"))
        self.patient_row["Name"] = patient.get("full_name", self.patient_row.get("Name"))
        self.patient_row["Sex"] = patient.get("gender", self.patient_row.get("Sex"))
        self.patient_row["Phone"] = patient.get("phone", self.patient_row.get("Phone"))

        if hasattr(self, "summary_label"):
            self.summary_label.setText(self._summary_text())

        # ---------------------------------------------------------
        # STAGE 3 - STEP 1.1: SYNC HISTORY TAB FROM BACKEND
        # ---------------------------------------------------------
        # Clear existing local session history to prevent duplicates
        self._result_history = []
        self._history_payloads = {}

        def _is_empty_placeholder(r: dict) -> bool:
            status = str(r.get("status", "") or "").strip().lower()
            values = r.get("values") or {}
            notes = str(r.get("notes", "") or "").strip()
            return status == "draft" and not values and not notes

        for r in results:
            if not isinstance(r, dict) or _is_empty_placeholder(r):
                continue

            rid = r.get("id")
            event_id = f"hist_{rid}"
            t_id = int(r.get("test_type_id") or 0)
            t_name = test_types.get(t_id, f"Test #{t_id}")

            # Map backend result to history event structure
            event = {
                "event_id": event_id,
                "time": r.get("updated_at") or r.get("created_at") or "N/A",
                "test": t_name,
                "type": r.get("template_snapshot", {}).get("kind", "table"),
                "status": r.get("status", "completed"),
                "revision": 1, 
                "request_id": r.get("test_request_id"),
            }

            self._result_history.append(event)
            
            # CRITICAL: Store the actual backend result object as the payload.
            # This allows the 'Edit' and 'Reprint' buttons to find the data they need.
            self._history_payloads[event_id] = r

        # Refresh the History Table UI
        if hasattr(self, "_refresh_history_table"):
            self._refresh_history_table()
        # ---------------------------------------------------------

        # 2. Fill Backend Results Table (Existing Logic)
        rows = []
        hidden_count = 0
        for r in results:
            if isinstance(r, dict) and _is_empty_placeholder(r):
                hidden_count += 1
                continue

            rid = r.get("id")
            tname = test_types.get(int(r.get("test_type_id", 0)), f"TestType #{r.get('test_type_id')}")
            rows.append({
                "Result ID": rid,
                "Test": tname,
                "Status": r.get("status"),
                "Created At": r.get("created_at"),
                "Updated At": r.get("updated_at"),
                "_result_id": rid,  # hidden id for selection
            })

        if hasattr(self, "backend_results_table"):
            self.backend_results_table.set_rows(rows)

        if hasattr(self, "backend_status"):
            msg = f"Loaded {len(rows)} result(s) from backend."
            if hidden_count:
                msg += f" (Hidden {hidden_count} empty draft placeholder(s).)"
            self.backend_status.setText(msg)


    def _on_backend_failed(self, msg: str):
        if hasattr(self, "backend_status"):
            self.backend_status.setText("Backend load failed.")
        QMessageBox.warning(self, "Backend Unreachable", msg)


    def _on_backend_done(self):
        if hasattr(self, "btn_backend_refresh"):
            self.btn_backend_refresh.setEnabled(True)


    def _backend_open_selected(self, row: dict):
        rid = row.get("_result_id") or row.get("Result ID")
        if not rid:
            QMessageBox.information(self, "No selection", "Select a backend result first.")
            return

        bp = BackendProfile.load()
        if not bp.enabled:
            QMessageBox.information(self, "Disabled", "Enable backend integration in Settings first.")
            return

        # Run detail fetch in a short thread to keep UI responsive
        t = QThread(self)
        w = _ResultDetailWorker(
            base_url=bp.base_url,
            timeout_s=bp.timeout_s,
            result_id=int(rid)
        )
        w.moveToThread(t)

        def ok(result_detail: dict):
            t.quit()

            # Minimal professional read-only dialog: show key facts + values/flags
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Backend Result (Read-only)")
            status = result_detail.get("status")
            values = result_detail.get("values", {})
            flags = result_detail.get("flags", {})
            dlg.setText(
                f"Result ID: {result_detail.get('id')}\n"
                f"Status: {status}\n"
                f"Created: {result_detail.get('created_at')}\n\n"
                f"Values: {values}\n\n"
                f"Flags: {flags}"
            )
            dlg.exec()

        def fail(msg: str):
            t.quit()
            QMessageBox.warning(self, "Load Failed", msg)

        t.started.connect(w.run)
        w.finished.connect(ok)
        w.failed.connect(fail)
        w.finished.connect(t.deleteLater)
        w.failed.connect(t.deleteLater)
        t.start()
        
    def _resolve_backend_ids_for_request(self, req: dict) -> tuple[int, int | None]:
        # Prefer backend-provided test_type_id
        if req.get("test_type_id"):
            tt = int(req["test_type_id"])
            if tt == 2:  # WIDAL
                return (2, None)
            if tt == 1:  # FBC
                return (1, 1)
            return (tt, None)

        # Fallback legacy name mapping (safe)
        name = (req.get("test_name") or "").strip().lower()
        if "full blood count" in name or "fbc" in name:
            return (1, 1)
        if "widal" in name:
            return (2, None)
        return (1, 1)



    def _backend_instantiate_result(self, test_type_id: int, template_id: int) -> dict:
        from shared.net.api_client import ApiClient, ApiConfig
        from shared.config.backend_profile import BackendProfile

        bp = BackendProfile.load()
        if not bp.enabled:
            raise RuntimeError("Backend integration is disabled in Settings.")
        if not self.patient_id:
            raise RuntimeError("Missing backend patient id for this profile.")

        api = ApiClient(ApiConfig(
            base_url=bp.base_url,
            timeout_s=bp.timeout_s,
        ))

        body = {
            "patient_id": int(self.patient_id),
            "test_type_id": int(test_type_id),
            "template_id": int(template_id),
        }

        return api.post_json("/api/results/instantiate", body=body)
    
    def _backend_instantiate_from_snapshot(
        self,
        test_type_id: int,
        template_snapshot: dict,
        values: dict,
        notes: str | None = None,
    ) -> dict:
        api = self._backend_api()
        if not self.patient_id:
            raise RuntimeError("Missing backend patient id for this profile.")

        body = {
            "patient_id": int(self.patient_id),
            "test_type_id": int(test_type_id),
            "template_id": None,
            "template_snapshot": template_snapshot or {},
            "values": values or {},
            "notes": notes,
        }
        return api.post_json("/api/results/from-snapshot", body=body)

    def _backend_api(self):
        from shared.net.api_client import ApiClient, ApiConfig
        from shared.config.backend_profile import BackendProfile
        bp = BackendProfile.load()
        return ApiClient(ApiConfig(
            base_url=bp.base_url,
            timeout_s=bp.timeout_s,
        ))

    def _structured_payload_to_backend_values(self, backend_result_id: int, payload: dict) -> dict:
        """
        Convert StructuredResultEditor payload rows (Parameter names) into backend values dict keyed by template_snapshot.fields[].key
        Example: "HB" -> "hb"
        """
        api = self._backend_api()
        r = api.get_json(f"/api/results/{backend_result_id}")

        snap = r.get("template_snapshot", {}) or {}
        fields = snap.get("fields", []) or []

        # label -> key map (case-insensitive)
        label_to_key = {}
        for f in fields:
            label = self._norm(str(f.get("label", "")))
            key = str(f.get("key", "")).strip()
            if label and key:
                label_to_key[label] = key


        values_out: dict = {}

        for row in payload.get("rows", []) or []:
            label = self._norm(str(row.get("parameter", "")))

            raw = str(row.get("result", "")).strip()
            if not label or not raw:
                continue

            key = label_to_key.get(label)
            if not key:
                # Unknown label in this backend template snapshot; skip safely
                continue

            try:
                values_out[key] = float(raw)
            except ValueError:
                # Non-numeric; skip (backend expects numbers for flagging)
                continue

        return values_out
    
    def _backend_update_values(self, backend_result_id: int, values: dict, notes: str | None = None) -> dict:
        api = self._backend_api()
        body = {"values": values}
        if notes is not None:
            body["notes"] = notes
        return api.patch_json(f"/api/results/{backend_result_id}/values", body=body)

    def _norm(self, s: str) -> str:
        return "".join(ch for ch in (s or "").lower() if ch.isalnum())

    def _normalize_backend_payload(self, backend_data: dict) -> dict:
        """
        Translates backend JSON into the local 'payload' format.
        """
        # 1. Identify the 'type' for the UI switch/case
        snapshot = backend_data.get("template_snapshot", {})
        kind = snapshot.get("kind", "table")
        
        # Map backend 'grid' or 'table' to the UI's expected strings
        ui_type = "structured" if kind in ["grid", "structured"] else "table"
        if kind == "pc_template":
            ui_type = "pc_template"

        # 2. Reconstruct the payload
        normalized = {
            "type": ui_type,
            "backend_id": backend_data.get("id"),
            "test_name": backend_data.get("test_name"),
            "request": {
                "request_id": backend_data.get("test_request_id"),
                "test_name": backend_data.get("test_name"),
                "patient_id": self.patient_id
            },
            "values": backend_data.get("values", {}),
            "notes": backend_data.get("notes", ""),
            # Structured editor specifically looks for 'rows'
            "rows": [] 
        }

        # 3. If it's a structured/table result, rebuild the row list from the snapshot
        fields = snapshot.get("fields", [])
        values = backend_data.get("values", {})
        for f in fields:
            key = f.get("key")
            normalized["rows"].append({
                "parameter": f.get("label", key),
                "result": str(values.get(key, "")),
                "unit": f.get("unit", ""),
                "reference": f.get("reference_range", ""),
                "key": key
            })

        return normalized
    # ---------------------------
    # Test Requests (Backend)
    # ---------------------------
    def _load_test_requests_from_backend(self) -> None:
        bp = BackendProfile.load()
        if not bp.enabled or not self.patient_id:
            return

        api = self._backend_api()

        # Test type name map
        try:
            tt_data = api.get_json("/api/test-types")
            tt_list = tt_data.get("value", []) if isinstance(tt_data, dict) else (tt_data if isinstance(tt_data, list) else [])
        except Exception:
            tt_list = []

        test_types: dict[int, str] = {}
        for t in tt_list:
            tid = t.get("id")
            if tid is None:
                continue
            name = (t.get("name") or "").strip() or f"TestType #{tid}"
            test_types[int(tid)] = name

        # ✅ Lab should read PAID (and optionally accepted) requests, not pending
        # ✅ Lab reads ONLY PAID requests (cashier gate)
        reqs = api.get_json(
            "/api/test-requests",
            params={"patient_id": int(self.patient_id), "status": "paid", "limit": 200},
        )
        if not isinstance(reqs, list):
            reqs = []


        self._requests = []
        for r in reqs:
            if not isinstance(r, dict):
                continue

            rid = r.get("id")
            tt_id = r.get("test_type_id")
            created_at = r.get("created_at")
            requested_by = r.get("requested_by") or "Reception"

            requested_at = str(created_at or "")
            if "T" in requested_at:
                requested_at = requested_at.replace("T", " ")[:16]

            self._requests.append(
                {
                    "request_id": str(rid),
                    "test_name": test_types.get(int(tt_id or 0), f"TestType #{tt_id}"),
                    "requested_by": requested_by,
                    "requested_at": requested_at,
                    "status": (r.get("status") or "").strip() or "paid",
                    "test_type_id": int(tt_id) if tt_id is not None else None,
                }
            )

        if hasattr(self, "requests_table"):
            self.requests_table.set_rows(self._requests_to_rows())



    def _backend_update_test_request_status(self, request_id: int, new_status: str) -> dict:
        api = self._backend_api()
        body = {"status": new_status}
        return api.patch_json(f"/api/test-requests/{int(request_id)}/status", body=body)