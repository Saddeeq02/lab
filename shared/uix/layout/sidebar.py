# shared/uix/layout/sidebar.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy


@dataclass(frozen=True)
class SidebarItem:
    key: str
    label: str
    icon: Optional[str] = None


class Sidebar(QWidget):

    route_clicked = Signal(str)

    def __init__(self, app_name: str, items: List[SidebarItem]):
        super().__init__()

        self.setFixedWidth(240)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # Important for QSS targeting
        self.setObjectName("Sidebar")

        self._items = items
        self._buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 20)
        root.setSpacing(6)

        # Title
        title = QLabel(app_name)
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setProperty("sidebarTitle", True)
        root.addWidget(title)

        root.addSpacing(16)

        # Buttons
        for item in self._items:
            btn = QPushButton(item.label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(40)

            # Dynamic properties for QSS
            btn.setProperty("sidebar", True)
            btn.setProperty("active", False)

            btn.clicked.connect(lambda _, k=item.key: self.route_clicked.emit(k))

            self._buttons[item.key] = btn
            root.addWidget(btn)

        root.addStretch()

    def set_active(self, route_key: str) -> None:
        for key, btn in self._buttons.items():
            is_active = (key == route_key)
            btn.setProperty("active", is_active)

            # Refresh style
            btn.style().unpolish(btn)
            btn.style().polish(btn)