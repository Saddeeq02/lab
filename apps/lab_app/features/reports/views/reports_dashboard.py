# apps/lab_app/features/reports/views/reports_dashboard.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QFrame, QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from shared.net.api_client import ApiError



class ReportsDashboardView(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- 1. Header Section ---
        header_layout = QHBoxLayout()
        title_container = QVBoxLayout()
        
        self.title = QLabel("Clinical Reports")
        self.title.setObjectName("PageTitle") # Styled in solunex.qss
        
        self.subtitle = QLabel("Manage verification, approval, and distribution of laboratory results.")
        self.subtitle.setStyleSheet("color: #64748b; font-size: 14px;")
        
        title_container.addWidget(self.title)
        title_container.addWidget(self.subtitle)
        header_layout.addLayout(title_container)
        
        # Stats Summary (Quick Glance)
        self.stats_label = QLabel("12 Pending Approval")
        self.stats_label.setStyleSheet("""
            background-color: #FEF3C7; color: #92400E; 
            padding: 8px 15px; border-radius: 15px; font-weight: bold;
        """)
        header_layout.addStretch()
        header_layout.addWidget(self.stats_label)
        layout.addLayout(header_layout)

        # --- 2. Action & Filter Bar ---
        filter_frame = QFrame()
        filter_frame.setObjectName("Card") # White background with border
        filter_layout = QHBoxLayout(filter_frame)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Patient Name or Lab ID...")
        self.search_input.setMinimumHeight(40)
        
        self.refresh_btn = QPushButton("Refresh Data")
        self.refresh_btn.setProperty("role", "default")
        self.refresh_btn.setMinimumHeight(40)
        
        filter_layout.addWidget(self.search_input, 1)
        filter_layout.addWidget(self.refresh_btn)
        layout.addWidget(filter_frame)

        # --- 3. The Reports Ledger (Main Table) ---
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Lab ID", "Patient Name", "Tests Ordered", "Date", "Status", "Action"
        ])
        
        # Enterprise Table Styling
        h_header = self.table.horizontalHeader()
        h_header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False) # Cleaner look
        
        # ... (previous UI code) ...
        layout.addWidget(self.table)

        # --- 4. Signals & Timers ---
        from PySide6.QtCore import QTimer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)

        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.refresh_btn.clicked.connect(self.load_data)

    def on_search_text_changed(self, text):
        """Wait 300ms after typing stops before hitting the API"""
        self.search_timer.start(300)

    def on_activated(self):
        """Called by the Shell when this view is shown"""
        self.load_data()


    def load_data(self):
        """
        Triggered when view opens. Fetches joined data from the 
        new /api/reports/generate (or summary) endpoint.
        """
        # Logic to populate table goes here
        pass

    def create_status_badge(self, status):
        """Helper to create color-coded status indicators"""
        badge = QLabel(status)
        if status == "Draft":
            badge.setStyleSheet("color: #64748b; font-weight: bold;")
        elif status == "Reviewing":
            badge.setStyleSheet("color: #2563eb; font-weight: bold;")
        elif status == "Released":
            badge.setStyleSheet("color: #0F3D2E; font-weight: bold;")
        return badge


    def load_data(self):
        """Initial load of all relevant reports"""
        self.perform_search()

    # apps/lab_app/features/reports/views/reports_dashboard.py

    def perform_search(self):
        query = self.search_input.text()
        
        # Define the path based on whether there's a search term or not
        path = "/api/patients/search" if query else "/api/test-requests"
        params = {"q": query} if query else {}
        
        try:
            # USE THE CORRECT METHOD: get_json
            # This returns the actual DATA (list/dict), not a response object.
            data = self.api_client.get_json(path, params=params)
            
            if isinstance(data, list):
                self.populate_table(data)
            else:
                # Handle cases where the API might return a single object or error dict
                print(f"Unexpected data format: {data}")
                
        except ApiError as e:
            print(f"API Error ({e.status_code}): {e}")
            self.table.setRowCount(0)
        except Exception as e:
            print(f"Unexpected Error: {e}")

    def populate_table(self, data_list):
        self.table.setRowCount(0)
        if not data_list: return

        for row_idx, item in enumerate(data_list):
            self.table.insertRow(row_idx)
            self.table.setRowHeight(row_idx, 50)

            # 1. Lab ID
            req_id = item.get('id', 0)
            self.table.setItem(row_idx, 0, QTableWidgetItem(f"LPT-{req_id:04d}"))

            # 2. Patient Name (MATCHING YOUR MYSQL 'full_name' COLUMN)
            # We check the top level (Search) and the nested level (Refresh)
            patient_obj = item.get('patient') or {}
            
            # Try all possible keys where the name might hide
            name = (
                item.get('full_name') or            # If it's a Patient object
                patient_obj.get('full_name') or     # If it's a nested Patient object
                item.get('name') or                 # Fallback for old API keys
                "UNKNOWN PATIENT"
            )
            
            name_item = QTableWidgetItem(str(name).upper())
            name_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, name_item)

            # 3. Tests Ordered
            # Ensure we check for the test type name correctly
            test_type_obj = item.get('test_type') or {}
            test_name = (
                item.get('test_type_name') or 
                test_type_obj.get('name') or 
                "General Test"
            )
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(test_name)))

            # 4. Date
            date_raw = item.get('created_at', '2026-03-17')
            self.table.setItem(row_idx, 3, QTableWidgetItem(date_raw[:10]))

            # 5. Status
            status = str(item.get('status', 'Pending')).capitalize()
            badge = self.create_status_badge(status)
            badge.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row_idx, 4, badge)

            # 6. Action
            view_btn = QPushButton("View Report")
            view_btn.setProperty("variant", "primary")
            view_btn.setMinimumHeight(35)
            
            # Use the ID to connect the button
            request_id = item.get('id')
            view_btn.clicked.connect(lambda _, r_id=request_id: self.open_report(r_id))
            self.table.setCellWidget(row_idx, 5, view_btn)
    # apps/lab_app/features/reports/views/reports_dashboard.py

    def open_report(self, request_id):
        """Triggers the 'Source of Truth' Clinical Report"""
        try:
            # FIX: Use the exact route defined in your FastAPI Reports router
            # Path: /api/reports/clinical/{request_id}
            report_data = self.api_client.get_json(f"/api/reports/clinical/{request_id}")
            
            # Now show the dialog with the fetched data
            from apps.lab_app.features.reports.views.report_viewer import ReportPreviewDialog
            dialog = ReportPreviewDialog(report_data, self)
            
            if dialog.exec():
                # Logic for when they click 'Approve' (e.g., refreshing the list)
                self.load_data()

        except ApiError as e:
            # This will catch if the ReportService returns None (404)
            print(f"Could not load report details: {e}")
        except Exception as e:
            print(f"Unexpected UI Error: {e}")