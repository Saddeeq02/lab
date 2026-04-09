import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .api import AuthAPI
from shared.security.session import Session

CONFIG_FILE = "config.json"


class LoginView(QWidget):
    def __init__(self, router, api_client):
        super().__init__()
        self.router = router
        self.auth_api = AuthAPI(api_client)
        self.on_login_success = None

        self.setWindowTitle("I and E Lab – Secure Access")
        self.setFixedSize(460, 520)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # ---------- Card Container ----------
        card = QFrame()
        card.setObjectName("loginCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(18)

        # ---------- Title ----------
        title = QLabel("I and E Lab")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Enterprise Laboratory Management")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 11px;")

        # ---------- Server Configuration ----------
        server_label = QLabel("Hospital Server (IP)")
        server_label.setStyleSheet("color: #666; font-size: 10px; font-weight: 600; margin-bottom: -5px;")
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("e.g., 192.168.1.15")
        self.server_input.setFixedHeight(38)
        self.server_input.setText(self.auth_api.api_client.config.base_url)

        self.verify_button = QPushButton("Verify Connection")
        self.verify_button.setFixedHeight(30)
        self.verify_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f2f5;
                color: #4c6ef5;
                border: 1px solid #dcdfe6;
                font-size: 11px;
                font-weight: normal;
            }
            QPushButton:hover { background-color: #e4e7ed; }
        """)
        self.verify_button.clicked.connect(self._handle_verify_connection)

        # ---------- Inputs ----------
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setFixedHeight(40)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(40)

        self.password_input.returnPressed.connect(self._handle_login)

        # ---------- Button ----------
        self.login_button = QPushButton("Sign In")
        self.login_button.setFixedHeight(42)
        self.login_button.clicked.connect(self._handle_login)

        # ---------- Layout Assembly ----------
        card_layout.addStretch()
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(15)
        
        card_layout.addWidget(server_label)
        card_layout.addWidget(self.server_input)
        card_layout.addWidget(self.verify_button)
        card_layout.addSpacing(15)

        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.login_button)
        card_layout.addStretch()

        root.addWidget(card)

        self._apply_styles()

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f8;
                font-family: Segoe UI;
            }

            QFrame#loginCard {
                background-color: white;
                border-radius: 10px;
            }

            QLineEdit {
                border: 1px solid #d0d5dd;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }

            QLineEdit:focus {
                border: 1px solid #4c6ef5;
            }

            QPushButton {
                background-color: #4c6ef5;
                color: white;
                border-radius: 6px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #3b5bdb;
            }

            QPushButton:pressed {
                background-color: #364fc7;
            }
        """)

    def _handle_verify_connection(self):
        server_url = self.server_input.text().strip()
        if not server_url:
            QMessageBox.warning(self, "Error", "Please enter a Server IP or URL.")
            return

        # Simple normalization: add http:// if missing
        if not server_url.startswith("http"):
            server_url = f"http://{server_url}"
            self.server_input.setText(server_url)

        self.verify_button.setEnabled(False)
        self.verify_button.setText("Verifying...")

        try:
            self.auth_api.api_client.set_base_url(server_url)
            health = self.auth_api.api_client.health()
            if health.get("status") == "ok":
                QMessageBox.information(self, "Success", f"Successfully connected to {server_url}")
            else:
                raise Exception("Server returned non-OK status.")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Could not reach server: {e}")
        finally:
            self.verify_button.setEnabled(True)
            self.verify_button.setText("Verify Connection")

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        server_url = self.server_input.text().strip()

        if not server_url:
            QMessageBox.warning(self, "Error", "Server IP is required.")
            return

        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password required.")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in...")

        try:
            # Update API Client one last time before login
            self.auth_api.api_client.set_base_url(server_url)
            
            data = self.auth_api.login(username, password)

            access_token = data.get("access_token")
            user = data.get("user")

            if not access_token or not user:
                raise Exception("Invalid authentication response from server.")

            role = user.get("role")
            branch_id = user.get("branch_id")

            if role not in {"lab_staff", "super_admin"}:
                QMessageBox.warning(self, "Unauthorized", "Access denied for this role.")
                return

            if branch_id is None and role != "super_admin":
                QMessageBox.warning(self, "Configuration Error", "User not assigned to branch.")
                return

            Session.start(access_token, user)
            
            # ✅ Save successful Server IP
            self._save_server_config(server_url)

            if self.on_login_success:
                self.on_login_success()

        except Exception as e:
            QMessageBox.warning(self, "Login Failed", str(e))

        finally:
            self.login_button.setEnabled(True)
            self.login_button.setText("Sign In")

    def _save_server_config(self, url: str):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"server_url": url}, f)
        except Exception as e:
            print(f"Config Save Error: {e}")