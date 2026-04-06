from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from .api import AuthAPI
from shared.security.session import Session


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
        card_layout.addSpacing(20)
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

    def _handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and password required.")
            return

        self.login_button.setEnabled(False)
        self.login_button.setText("Signing in...")

        try:
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

            if self.on_login_success:
                self.on_login_success()

        except Exception as e:
            QMessageBox.warning(self, "Login Failed", str(e))

        finally:
            self.login_button.setEnabled(True)
            self.login_button.setText("Sign In")