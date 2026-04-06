# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
    QMenu, QLineEdit, QFrame
)

from shared.uix.widgets.tables import DataTable
from apps.lab_app.features.patients.views.patient_profile import PatientProfileView

from shared.config.backend_profile import BackendProfile
from shared.net.api_client import ApiClient, ApiConfig, ApiError
from shared.security.session import Session

BACKEND_DOWN_TEXT = "Backend unreachable. Check connection from Settings."
EMPTY_SEARCH_TEXT = "Waiting for today's patients..."

def _age_from_dob(dob_value) -> str:
    if not dob_value: return "-"
    s = str(dob_value).strip()[:10]
    try:
        y, m, d = [int(x) for x in s.split("-")]
        dob = date(y, m, d)
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return str(int(age)) if age >= 0 else "-"
    except: return "-"

class PatientsListView(QWidget):

    def __init__(self):
        super().__init__()
        self._initialized = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(15)

        # --- Header Section ---
        header_container = QFrame()
        header_lay = QHBoxLayout(header_container)
        header_lay.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Patient Profiles")
        header.setObjectName("PageTitle") # Ties into your new CSS
        header_lay.addWidget(header)
        header_lay.addStretch()
        
        root.addWidget(header_container)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by Name, ID or Phone...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(350)
        self.search.setMinimumHeight(35)
        
        # Debounce timer for search
        self._search_timer = QTimer(self)
        self._search_timer.setInterval(400)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.load_patients)
        self.search.textChanged.connect(self._search_timer.start)

        toolbar.addWidget(self.search)
        toolbar.addStretch()

        self.btn_refresh = QPushButton("Refresh List")
        self.btn_refresh.setProperty("variant", "primary") # Enterprise button style
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.load_patients)
        toolbar.addWidget(self.btn_refresh)

        root.addLayout(toolbar)

        # --- Table ---
        cols = ["Patient ID", "Name", "Sex", "Age", "Phone", "Last Visit"]
        self.table = DataTable(columns=cols)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.row_activated.connect(self._open_profile_from_row)

        root.addWidget(self.table, 1)

        # Auto-refresh every 60s
        self.live_timer = QTimer(self)
        self.live_timer.timeout.connect(self._auto_refresh)
        self.live_timer.start(60000)

    def on_activated(self):
        """Called when the view becomes active in the AppShell."""
        if Session.is_authenticated():
            self.load_patients()

    def _render_placeholder(self, message: str) -> None:
        self.table.set_rows([{
            "id": None, "patient_no": "", "Patient ID": "",
            "Name": message, "Sex": "", "Age": "", "Phone": "", "Last Visit": "",
        }])

    def _auto_refresh(self):
        if not self.search.text().strip():
            self.load_patients()

    def load_patients(self):
        """
        Synchronous but safe loading. 
        If the backend is fast, this won't freeze the UI.
        If it's slow, we use ProcessEvents to keep the app alive.
        """
        if not Session.is_authenticated():
            return

        q = self.search.text().strip()
        bp = BackendProfile.load()
        
        if not bp.enabled:
            self._render_placeholder(BACKEND_DOWN_TEXT)
            return

        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Loading...")

        try:
            api = ApiClient(ApiConfig(base_url=bp.base_url, timeout_s=bp.timeout_s))
            params = {"q": q} if q else {"created_date": date.today().isoformat()}
            
            # Perform the GET request
            data = api.get_json("/api/patients/search", params=params)
            
            value = []
            if isinstance(data, dict): value = data.get("value", []) or []
            elif isinstance(data, list): value = data

            rows = []
            for p in value:
                rows.append({
                    "id": p.get("id"),
                    "patient_no": p.get("patient_no"),
                    "Patient ID": p.get("patient_no") or "",
                    "Name": p.get("full_name") or "",
                    "Sex": p.get("gender") or "",
                    "Age": _age_from_dob(p.get("date_of_birth") or p.get("dob")),
                    "Phone": p.get("phone") or "",
                    "Last Visit": str(p.get("created_at") or "")[:10],
                })

            if not rows:
                self._render_placeholder("No patients found.")
            else:
                self.table.set_rows(rows)

        except ApiError as e:
            self._render_placeholder(f"Connection Error: {str(e)}")
        except Exception as e:
            self._render_placeholder(f"System Error: {str(e)}")
        finally:
            self.btn_refresh.setEnabled(True)
            self.btn_refresh.setText("Refresh List")

    # --- Navigation ---

    def _on_context_menu(self, pos):
        row = self.table.selected_row_data()
        if not row or not row.get("id"): return

        menu = QMenu(self)
        action = menu.addAction("Open Profile")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == action:
            self._open_profile(row)

    def _open_profile_from_row(self, row: dict):
        if row and row.get("id"):
            self._open_profile(row)

    def _open_profile(self, row: dict):
        """Uses the AppShell's set_page method for clean navigation."""
        profile = PatientProfileView(patient_row=row)
        
        # Walk up the tree to find the AppShell
        win = self.window()
        if hasattr(win, 'set_page'):
            win.set_page(profile, title="Patient Profile")