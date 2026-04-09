import sys
import json
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from shared.net.api_client import ApiClient, ApiConfig
from shared.security.session import Session
from shared.uix.layout.shell import AppShell
from shared.uix.theme.theme import load_solunex_theme 

from apps.lab_app.routes import LabRoutes
from apps.lab_app.features.auth.view import LoginView

CONFIG_FILE = "config.json"
DEFAULT_API_BASE_URL = "http://192.168.1.15:8000"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"server_url": DEFAULT_API_BASE_URL}

def main():
    config = load_config()
    server_url = config.get("server_url", DEFAULT_API_BASE_URL)
   
    
    app = QApplication(sys.argv)

    # 2. Apply Global Theme
    try:
        app.setStyleSheet(load_solunex_theme())
    except Exception as e:
        print(f"Theme Load Warning: {e}")

    # 3. Initialize Core Services
    api_client = ApiClient(ApiConfig(base_url=server_url))
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
            api_client=api_client, 
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