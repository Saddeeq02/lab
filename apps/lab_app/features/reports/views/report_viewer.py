from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class ReportPreviewDialog(QDialog):
    def __init__(self, report_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Medical Report Verification")
        self.resize(850, 750)
        self.data = report_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # --- 1. Header (Branded & Detailed) ---
        header = QFrame()
        header.setObjectName("Card") # Reusing your card style
        header.setStyleSheet("""
            QFrame#Card { 
                background-color: #f8fafc; 
                border: 1px solid #e2e8f0; 
                border-radius: 12px; 
            }
        """)
        h_layout = QVBoxLayout(header)
        
        lab_title = QLabel("SOLUNEX CLINICAL LABORATORY")
        lab_title.setStyleSheet("font-weight: 800; font-size: 20px; color: #0F3D2E;")
        
        # MAPPING: Pull from nested 'patient' and 'metadata'
        p_info = self.data.get('patient', {})
        meta = self.data.get('metadata', {})
        
        name = p_info.get('name', 'N/A').upper()
        uid = p_info.get('uid', '---')
        age_sex = f"{p_info.get('age', '??')}Y / {p_info.get('sex', '?')}"
        date = meta.get('created_at', '')[:16].replace('T', ' ')
        
        details = QLabel(f"Patient: {name} ({age_sex}) | UID: {uid} | Date: {date}")
        details.setStyleSheet("color: #475569; font-size: 13px; font-weight: 500;")
        
        h_layout.addWidget(lab_title)
        h_layout.addWidget(details)
        layout.addWidget(header)

        # --- 2. Clinical Results Table ---
        results_label = QLabel("LABORATORY FINDINGS")
        results_label.setStyleSheet("font-weight: bold; color: #1e293b; margin-top: 10px;")
        layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Test Parameter", "Result", "Reference Range"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setShowGrid(False)
        
        # MAPPING: Accessing the 'clinical_data' block
        clinical = self.data.get('clinical_data', {})
        results = clinical.get('results', {}) or {}
        flags = clinical.get('flags', {}) or {}
        snapshot = clinical.get('snapshot', {}) or {}
        
        self.results_table.setRowCount(0)
        for row, (test_key, value) in enumerate(results.items()):
            self.results_table.insertRow(row)
            
            # Parameter
            self.results_table.setItem(row, 0, QTableWidgetItem(test_key))
            
            # Result + Flagging
            result_text = str(value)
            flag = flags.get(test_key, "Normal")
            
            res_item = QTableWidgetItem(result_text)
            
            # If the result is abnormal, color it Red and add the flag (e.g., "140 (High)")
            if flag in ["High", "Low", "Critical"]:
                res_item.setForeground(QColor("#dc2626")) # Modern Red
                res_item.setText(f"{result_text} ({flag})")
            
            self.results_table.setItem(row, 1, res_item)
            
            # Reference Range (from the snapshot saved at time of test)
            ref_info = snapshot.get(test_key, {})
            range_text = f"{ref_info.get('range', 'N/A')} {ref_info.get('unit', '')}"
            self.results_table.setItem(row, 2, QTableWidgetItem(range_text))

        layout.addWidget(self.results_table)

        # --- 3. Footer (Notes & Actions) ---
        notes_text = clinical.get('notes')
        if notes_text:
            notes_lbl = QLabel(f"<b>Pathologist Notes:</b> {notes_text}")
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet("color: #64748b; font-style: italic;")
            layout.addWidget(notes_lbl)

        btn_layout = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.setMinimumHeight(40)
        
        self.approve_btn = QPushButton("Verify & Release Report")
        self.approve_btn.setProperty("variant", "primary") # Solunex Green
        self.approve_btn.setMinimumHeight(40)
        self.approve_btn.setMinimumWidth(200)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        btn_layout.addWidget(self.approve_btn)
        layout.addLayout(btn_layout)

        # Signals
        self.close_btn.clicked.connect(self.reject)
        self.approve_btn.clicked.connect(self.accept)