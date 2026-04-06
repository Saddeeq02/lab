import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from shared.net.api_client import ApiClient, ApiConfig
from shared.security.session import Session
from shared.uix.layout.shell import AppShell
from shared.uix.theme.theme import load_solunex_theme 

from apps.lab_app.routes import LabRoutes
from apps.lab_app.features.auth.view import LoginView

API_BASE_URL = "https://api.iandelaboratory.com"

def main():
   
    
    app = QApplication(sys.argv)

    # 2. Apply Global Theme
    try:
        app.setStyleSheet(load_solunex_theme())
    except Exception as e:
        print(f"Theme Load Warning: {e}")

    # 3. Initialize Core Services
    api_client = ApiClient(ApiConfig(base_url=API_BASE_URL))
    routes = LabRoutes(api_client=api_client)
    
    # Persistent reference to the shell
    main_shell: AppShell = None

    # apps/lab_app/main.py

    def show_shell():
        nonlocal main_shell
        main_shell = AppShell(
            app_name="I and E Laboratory System",
            sidebar_items=routes.sidebar_items(),
            route_resolver=routes.resolve,
            api_client=api_client,  # <--- ADD THIS LINE HERE
        )
        main_shell.show()

    def show_login():
        login_window = LoginView(router=None, api_client=api_client)

        def on_success():
            # Standard Enterprise Flow: Close Login -> Open Shell
            login_window.close()
            show_shell()

        login_window.on_login_success = on_success
        login_window.show()
        
        # Keep reference to prevent the Login Window from being garbage collected instantly
        app._login_window = login_window

    # 4. Entry Point Logic
    if Session.is_authenticated():
        show_shell()
    else:
        show_login()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()