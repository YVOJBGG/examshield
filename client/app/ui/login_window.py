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
from app.services.monitoring_client import MonitoringClient
from app.services.network_client import ApiClientError
from app.services.quiz_manager import QuizManager
from app.services.violation_service import ViolationService
from app.ui.exam_window import ExamWindow


class LoginWindow(QWidget):
    def __init__(
        self,
        auth_manager: AuthManager,
        quiz_manager: QuizManager,
        monitoring_client: MonitoringClient,
        violation_service: ViolationService,
    ) -> None:
        super().__init__()
        self.auth_manager = auth_manager
        self.quiz_manager = quiz_manager
        self.monitoring_client = monitoring_client
        self.violation_service = violation_service
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
        self.monitoring_client.clear_session()
        try:
            self.auth_manager.login(username, password)
            exam = self.quiz_manager.load_exam(exam_id)
            attempt_id = self.quiz_manager.start_attempt()
            self.monitoring_client.set_session(exam_id=exam.id, attempt_id=attempt_id)
            self.monitoring_client.send_connected(message="Student connected to exam session")
            self.exam_window = ExamWindow(
                quiz_manager=self.quiz_manager,
                monitoring_client=self.monitoring_client,
                violation_service=self.violation_service,
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
