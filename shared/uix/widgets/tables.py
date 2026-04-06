# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Any, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QTableWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QHeaderView
)

class SortableTableItem(QTableWidgetItem):
    """
    Custom table item that intelligently sorts numerical values 
    instead of treating everything like a string.
    """
    def __lt__(self, other: QTableWidgetItem) -> bool:
        text1 = self.text().strip()
        text2 = other.text().strip()
        
        # Handle empty values or the "-" dash from your age formatter
        # This ensures empty values sink to the bottom when sorting
        if not text1 or text1 == "-": return True
        if not text2 or text2 == "-": return False

        # Attempt to parse as numbers for proper numerical sorting (handles ints and floats)
        try:
            return float(text1) < float(text2)
        except ValueError:
            # Fallback to standard string comparison for names, IDs, etc.
            return text1.lower() < text2.lower()


class DataTable(QTableWidget):
    """
    Enterprise-Grade Data Table:
    - High-contrast Blue-Black/White styling.
    - Automated row zebra-striping.
    - Smooth content-aware resizing.
    - Intelligent Numerical Sorting.
    - Immutable Data Binding (Index-Safe).
    """

    row_activated = Signal(dict)

    def __init__(self, columns: List[str]):
        # Initialize with columns, but let rows be dynamic
        super().__init__(0, len(columns))
        self._columns = columns
        self._rows: list[dict] = []

        # --- [1] ENTERPRISE BEHAVIOR ---
        self.setHorizontalHeaderLabels(columns)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Enable professional features
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False) # Cleaner "modern" look (uses borders instead)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Removes ugly dotted focus rect

        # --- [2] HEADER STYLING ---
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Hide the vertical row numbers (looks amateur in enterprise tools)
        self.verticalHeader().setVisible(False)

        # Connect events
        self.cellDoubleClicked.connect(self._emit_row_activated)

    def set_rows(self, rows: List[dict]) -> None:
        """
        Populate the table with laboratory data.
        """
        self.setSortingEnabled(False) 
        self._rows = rows
        self.setRowCount(len(rows))

        for r_idx, row in enumerate(rows):
            for c_idx, col_name in enumerate(self._columns):
                val = row.get(col_name, "")
                
                # Using the custom SortableTableItem
                item = SortableTableItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                # --- FIX: Store the raw patient dictionary invisibly inside the first column ---
                if c_idx == 0:
                    item.setData(Qt.UserRole, row)
                
                self.setItem(r_idx, c_idx, item)

        self.setSortingEnabled(True)
        self.resizeColumnsToContents()
        
        for i in range(len(self._columns)):
            current_width = self.columnWidth(i)
            self.setColumnWidth(i, current_width + 20)

    def selected_row_data(self) -> Optional[dict]:
        idxs = self.selectionModel().selectedRows()
        if not idxs:
            return None
        
        # Get the visual row index on the screen
        visible_row = idxs[0].row()
        
        # Pull the dictionary directly out of the hidden UserRole data in Column 0
        item = self.item(visible_row, 0)
        if item:
            return item.data(Qt.UserRole)
            
        return None

    def _emit_row_activated(self, row: int, col: int) -> None:
        """Called when a user double-clicks a row"""
        # Pull the dictionary directly from the clicked visual row
        item = self.item(row, 0)
        if item:
            row_data = item.data(Qt.UserRole)
            if row_data:
                self.row_activated.emit(row_data)