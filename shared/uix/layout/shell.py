# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Any, Optional
from datetime import datetime

from PySide6.QtCore import Qt, QThread, QTimer, QSize
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QFrame, QScrollArea, QPushButton, QGraphicsDropShadowEffect
)
from shared.net.workers import NotificationPollingWorker
from shared.uix.layout.sidebar import Sidebar, SidebarItem
from shared.net.api_client import ApiClient

class AppShell(QMainWindow):
    def __init__(
        self,
        app_name: str,
        sidebar_items: list[Any],
        route_resolver: Callable[[str, "AppShell"], None],
        api_client: Optional[ApiClient] = None
    ):
        super().__init__()
        
        # --- [1] STATE & THREAD REGISTRY ---
        self.api_client = api_client
        self._app_name = app_name
        self._route_resolver = route_resolver
        self._active_route: Optional[str] = None
        self._active_threads: list[QThread] = []
        
        self.setWindowTitle(app_name)
        self.resize(1280, 800)

        # --- [2] CORE UI INITIALIZATION (ORDER FIXED) ---
        central = QWidget()
        central.setObjectName("MainWindow") 
        self.setCentralWidget(central)
        
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 1. Sidebar Setup
        items = [SidebarItem(key=i.key, label=i.label, icon=getattr(i, "icon", None)) for i in sidebar_items]
        self.sidebar = Sidebar(app_name=app_name, items=items)
        self.sidebar.route_clicked.connect(self._on_route_clicked)

        # 2. Right Content Container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(24, 20, 24, 24) 
        right_layout.setSpacing(15)

        # 3. Topbar Construction
        self.topbar = QFrame()
        self.topbar.setObjectName("Topbar")
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(0, 0, 0, 10)
        
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        self.page_title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2f3542;")
        topbar_layout.addWidget(self.page_title)
        
        topbar_layout.addStretch()

        # Modern Notification Badge
        self.notif_btn = QPushButton("0")
        self.notif_btn.setFixedSize(36, 36)
        self.notif_btn.setObjectName("NotificationBadge")
        self.notif_btn.setCursor(Qt.PointingHandCursor)
        self.notif_btn.setProperty("has_notifications", False)
        self.notif_btn.clicked.connect(self._show_notifications)
        
        # Add subtle shadow to badge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 2)
        self.notif_btn.setGraphicsEffect(shadow)
        
        topbar_layout.addWidget(self.notif_btn)

        # 4. Universal Scroll System (LIFO STABILIZED)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setObjectName("MainScrollArea")
        self.scroll_area.setFocusPolicy(Qt.NoFocus) # Fixes the "swapping/jumping" issue
        
        # FIXED: Initialize content host BEFORE route resolution
        self.content_host = QWidget()
        self.content_host.setObjectName("ContentHost")
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)
        self.content_layout.setAlignment(Qt.AlignTop) 

        self.scroll_area.setWidget(self.content_host)

        # Assemble Main View
        right_layout.addWidget(self.topbar)
        right_layout.addWidget(self.scroll_area, 1)
        outer.addWidget(self.sidebar)
        outer.addWidget(right_container, 1)

        # --- [3] MODERN STYLING ---
        self.setStyleSheet("""
            QMainWindow#MainWindow { background-color: #f8f9fa; }
            QLabel#PageTitle { color: #2d3436; }
            
            QPushButton#NotificationBadge {
                background-color: #ffffff;
                color: #636e72;
                border-radius: 18px;
                border: 1px solid #dfe6e9;
                font-weight: 800;
                font-size: 10px;
            }
            QPushButton#NotificationBadge[has_notifications="true"] {
                background-color: #ff7675;
                color: white;
                border: 1px solid #d63031;
            }
            QPushButton#NotificationBadge:hover {
                background-color: #f1f2f6;
            }
        """)

        # --- [4] INITIALIZATION & POLLING ---
        self._notif_timer = QTimer(self)
        self._notif_timer.timeout.connect(self._check_for_new_requests)
        self._notif_timer.start(20000) # Poll every 20s for snappier feel

        if items:
            self._on_route_clicked(items[0].key)

    # --- [NOTIFICATION LOGIC] ---
    def _check_for_new_requests(self):
        if not self.api_client: return
        if hasattr(self, "_poll_thread") and self._poll_thread.isRunning(): return

        self._poll_thread = QThread()
        self._poll_worker = NotificationPollingWorker(self.api_client) 
        self._poll_worker.moveToThread(self._poll_thread)
        
        self._poll_thread.started.connect(self._poll_worker.run)
        self._poll_worker.count_updated.connect(self.update_notification_count)
        
        self._poll_worker.count_updated.connect(self._poll_thread.quit)
        self._poll_thread.finished.connect(self._poll_thread.deleteLater)
        
        self.register_thread(self._poll_thread)
        self._poll_thread.start()

    def update_notification_count(self, count: int):
        self.notif_btn.setText(str(count) if count < 100 else "99+")
        
        has_notifs = count > 0
        self.notif_btn.setProperty("has_notifications", has_notifs)
        
        # Refresh stylesheet properties
        self.notif_btn.style().unpolish(self.notif_btn)
        self.notif_btn.style().polish(self.notif_btn)
        
        if has_notifs:
            self.notif_btn.setToolTip(f"Critical: {count} pending lab requests")
        else:
            self.notif_btn.setToolTip("No new laboratory requests")

    def _show_notifications(self):
        self._on_route_clicked("notifications")

    # --- [NAVIGATION & LIFO PROTECTION] ---
    def set_page(self, widget: QWidget, title: Optional[str] = None) -> None:
        """Sets the current active page widget with LIFO stability."""
        # 1. Clear existing content
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if (w := item.widget()):
                w.deleteLater() 

        # 2. Modernize transition and prevent focus-jumping
        widget.setAttribute(Qt.WA_LayoutUsesWidgetRect)

        # 3. Add to host
        self.content_layout.addWidget(widget)
        
        # 4. Force top-aligned view for LIFO
        self.scroll_area.verticalScrollBar().setValue(0)
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(0))

        # 5. Handle Title
        if title:
            self.page_title.setText(title)
        elif self._active_route:
            self.page_title.setText(self._active_route.replace("_", " ").upper())

    def _on_route_clicked(self, route_key: str) -> None:
        self._active_route = route_key
        self.sidebar.set_active(route_key)
        self._route_resolver(route_key, self)

    # --- [LIFECYCLE] ---
    def register_thread(self, thread: QThread):
        if thread not in self._active_threads:
            self._active_threads.append(thread)
            thread.finished.connect(
                lambda: self._active_threads.remove(thread) if thread in self._active_threads else None
            )

    def closeEvent(self, event):
        self._notif_timer.stop()
        for thread in self._active_threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()
        event.accept()

    def on_logout(self) -> None:
        self.close()