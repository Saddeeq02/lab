from dataclasses import dataclass
from typing import Optional, Any

from apps.lab_app.features.patients.views.patients_list import PatientsListView
from apps.lab_app.features.reports.views.reports_dashboard import ReportsDashboardView
from apps.lab_app.features.settings.views.settings_view import SettingsView
from apps.lab_app.features.test_types.views.test_types_view import TestTypesView
# Import the new Notification View we discussed
from apps.lab_app.features.notifications.view import NotificationListView

@dataclass(frozen=True)
class SidebarItem:
    key: str
    label: str
    icon: Optional[str] = None

class LabRoutes:
    def __init__(self, api_client=None): 
        self.api_client = api_client
        self._views = {
            "patients": PatientsListView,
            "reports": ReportsDashboardView,
            "test_types": TestTypesView,
            "settings": SettingsView,
            "notifications": NotificationListView, # Added for Topbar Badge
            "logout": None,
        }

    def sidebar_items(self) -> list[SidebarItem]:
        """Items visible in the left sidebar."""
        return [
            SidebarItem(key="patients", label="Profiles"),
            SidebarItem(key="reports", label="Reports"),
            SidebarItem(key="test_types", label="Test Types"),
            SidebarItem(key="settings", label="Settings"),
            SidebarItem(key="logout", label="Logout"),
        ]

    def resolve(self, route_key: str, shell: Any) -> None:
        """
        Handles navigation logic. Called by AppShell's sidebar 
        OR the AppShell's notification badge.
        """
        if route_key == "logout":
            shell.on_logout()
            return

        view_cls = self._views.get(route_key)
        if view_cls is None:
            return

        # --- REFINED DEPENDENCY INJECTION ---
        # 1. Handle Dashboard (Reports)
        if view_cls == ReportsDashboardView:
            view = view_cls(api_client=self.api_client)
        
        # 2. Handle Notifications (Mirror Profile Viewer)
        elif view_cls == NotificationListView:
            # We pass the shell so notifications can register background threads
            view = view_cls(api_client=self.api_client, shell=shell)
            
        # 3. Handle standard views
        else:
            view = view_cls()

        # Inject the new page into the shell's scrollable content area
        shell.set_page(view)

        # Enterprise lifecycle activation (Triggers data fetching, etc.)
        if hasattr(view, "on_activated"):
            view.on_activated()