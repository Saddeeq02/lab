# apps/lab_app/features/notifications/view.py
from __future__ import annotations
from PySide6.QtCore import QThread, Qt, Signal, QObject
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from shared.uix.widgets.tables import DataTable
from shared.net.api_client import ApiClient, ApiError

class _NotificationWorker(QObject):
    """Specialized worker to fetch raw Test Requests"""
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api = api_client

    def run(self):
        try:
            # We hit the endpoint we built in the FastAPI router
            # This returns the 'enriched' data (test_name, price, etc.)
            data = self.api.get_json("/api/test-requests", params={"status": "paid"})
            self.finished.emit(data if isinstance(data, list) else [])
        except Exception as e:
            self.failed.emit(str(e))

class NotificationListView(QWidget):

    def __init__(self, api_client=None, shell=None):
        super().__init__()
        self.api_client = api_client
        self.shell = shell
        self._thread = None

        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        self.title = QLabel("Incoming Lab Requests")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1E40AF;")
        header.addWidget(self.title)
        header.addStretch()
        
        self.btn_refresh = QPushButton("Refresh Queue")
        self.btn_refresh.clicked.connect(self.load_requests)
        header.addWidget(self.btn_refresh)
        layout.addLayout(header)

        # STAGE 2: Updated columns to reflect grouped data
        cols = ["Patient ID", "Patient Name", "Test Summary", "Status", "Requested By", "Time"]
        self.table = DataTable(columns=cols)
        layout.addWidget(self.table)

        self.status_label = QLabel("Loading queue...")
        layout.addWidget(self.status_label)

    def on_activated(self):
        """Triggered by the Route Resolver"""
        self.load_requests()

    def load_requests(self):
        if not self.api_client: return
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Fetching latest requests...")

        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        self._thread = QThread()
        self._worker = _NotificationWorker(self.api_client)
        self._worker.moveToThread(self._thread)
        
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        
        if self.shell:
            self.shell.register_thread(self._thread)
        self._thread.start()

    def _on_loaded(self, data: list):
        self.btn_refresh.setEnabled(True)
        
        if not data:
            self.table.set_rows([])
            self.status_label.setText("Total Pending: 0 (Queue Clear)")
            return

        # --- GROUPING LOGIC ---
        grouped = {}

        for item in data:
            pid = item.get("patient_id")
            test_name = item.get("test_name", "N/A")
            
            if pid not in grouped:
                grouped[pid] = {
                    "patient_id": pid,
                    "patient_name": item.get("patient_name", f"Patient {pid}"), 
                    "tests": [test_name],
                    "requested_by": item.get("requested_by"),
                    "time": item.get("created_at")
                }
            else:
                # Append the new test to this patient's list
                if test_name not in grouped[pid]["tests"]:
                    grouped[pid]["tests"].append(test_name)

        # --- FORMATTING FOR TABLE ---
        rows = []
        for pid, info in grouped.items():
            # Combine all tests into a single string separated by commas
            test_summary = ", ".join(info["tests"])
            
            rows.append({
                "id": pid, # Internal ID for deep-linking later
                "Patient ID": f"LPT-{pid}",
                "Patient Name": info["patient_name"],
                "Test Summary": test_summary,
                "Status": "PAID",
                "Requested By": info["requested_by"],
                "Time": str(info["time"])[:16].replace("T", " ")
            })
        
        self.table.set_rows(rows)
        self.status_label.setText(f"Patients Waiting: {len(rows)}")

    def _on_failed(self, error: str):
        self.btn_refresh.setEnabled(True)
        self.status_label.setText(f"Error: {error}")