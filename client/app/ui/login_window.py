from __future__ import annotations

from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import AUTOSAVE_INTERVAL_MS
from app.services.auth_manager import AuthManager
from app.services.network_client import ApiClientError
from app.services.quiz_manager import QuizManager
from app.ui.exam_window import ExamWindow


class LoginWindow(QWidget):
    def __init__(self, auth_manager: AuthManager, quiz_manager: QuizManager) -> None:
        super().__init__()
        self.auth_manager = auth_manager
        self.quiz_manager = quiz_manager
        self.exam_window: ExamWindow | None = None

        self.setWindowTitle("ExamShield Student Login")
        self.resize(420, 210)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("student1")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("student123")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.exam_id_input = QLineEdit()
        self.exam_id_input.setPlaceholderText("Exam UUID")

        self.login_button = QPushButton("Login and Open Exam")
        self.login_button.clicked.connect(self._on_login_clicked)

        self.status_label = QLabel("Enter credentials and assigned exam ID.")
        self.status_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Username", self.username_input)
        form.addRow("Password", self.password_input)
        form.addRow("Exam ID", self.exam_id_input)

        button_row = QHBoxLayout()
        button_row.addWidget(self.login_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def _on_login_clicked(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()
        exam_id = self.exam_id_input.text().strip()

        if not username or not password or not exam_id:
            QMessageBox.warning(self, "Missing fields", "Username, password, and exam ID are required.")
            return

        self.login_button.setEnabled(False)
        self.status_label.setText("Logging in and loading exam...")
        try:
            self.auth_manager.login(username, password)
            exam = self.quiz_manager.load_exam(exam_id)
            attempt_id = self.quiz_manager.start_attempt()
            self.exam_window = ExamWindow(
                quiz_manager=self.quiz_manager,
                autosave_interval_ms=AUTOSAVE_INTERVAL_MS,
            )
            self.exam_window.show()
            self.hide()
            self.status_label.setText(
                f"Started attempt {attempt_id} for {exam.title}.",
            )
        except ApiClientError as exc:
            self.status_label.setText("Login/exam setup failed.")
            QMessageBox.critical(self, "Request failed", str(exc))
        except Exception as exc:
            self.status_label.setText("Unexpected error.")
            QMessageBox.critical(self, "Error", str(exc))
        finally:
            self.login_button.setEnabled(True)
