from __future__ import annotations

from PyQt6.QtCore import QEvent, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import DEV_MODE, MONITORING_HEARTBEAT_INTERVAL_MS
from app.services.monitoring_client import MonitoringClient
from app.services.network_client import ApiClientError
from app.services.quiz_manager import QuizManager
from app.services.violation_service import ViolationService


class ExamWindow(QWidget):
    def __init__(
        self,
        quiz_manager: QuizManager,
        monitoring_client: MonitoringClient,
        violation_service: ViolationService,
        autosave_interval_ms: int = 25000,
    ) -> None:
        super().__init__()
        self.quiz_manager = quiz_manager
        self.monitoring_client = monitoring_client
        self.violation_service = violation_service
        self.autosave_interval_ms = autosave_interval_ms
        self._question_inputs: dict[str, QTextEdit] = {}
        self._submitted = False

        exam = self.quiz_manager.current_exam
        if exam is None:
            raise ValueError("Exam data is missing.")

        self.setWindowTitle("ExamShield Student Exam")
        self.resize(820, 650)

        self.title_label = QLabel(f"Exam: {exam.title}")
        self.time_limit_label = QLabel(f"Time limit: {exam.time_limit_minutes} minutes")
        self.status_label = QLabel("Attempt started.")
        self.monitoring_status_label = QLabel("Live monitoring unavailable")
        self.violation_status_label = QLabel("Violation reporting idle")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        for index, question in enumerate(exam.questions, start=1):
            question_label = QLabel(f"Q{index}. {question.text}")
            question_label.setWordWrap(True)
            answer_input = QTextEdit()
            answer_input.setPlaceholderText("Type your answer here...")
            answer_input.setPlainText(self.quiz_manager.get_answer(question.id))
            answer_input.textChanged.connect(
                self._build_text_changed_handler(question.id, answer_input)
            )
            content_layout.addWidget(question_label)
            content_layout.addWidget(answer_input)
            self._question_inputs[question.id] = answer_input

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)

        self.autosave_button = QPushButton("Autosave Now")
        self.autosave_button.clicked.connect(self._autosave_now)
        self.submit_button = QPushButton("Submit Exam")
        self.submit_button.clicked.connect(self._submit_exam)
        self.debug_violation_button = QPushButton("Trigger Test Violation")
        self.debug_violation_button.clicked.connect(self._trigger_test_violation)
        self.debug_violation_button.setVisible(DEV_MODE)

        button_row = QHBoxLayout()
        button_row.addWidget(self.autosave_button)
        button_row.addWidget(self.submit_button)
        if DEV_MODE:
            button_row.addWidget(self.debug_violation_button)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.time_limit_label)
        layout.addWidget(scroll_area)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.monitoring_status_label)
        layout.addWidget(self.violation_status_label)
        self.setLayout(layout)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(self.autosave_interval_ms)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

        self.monitoring_timer = QTimer(self)
        self.monitoring_timer.setInterval(MONITORING_HEARTBEAT_INTERVAL_MS)
        self.monitoring_timer.timeout.connect(self._send_heartbeat)
        self.monitoring_timer.start()

        self._set_monitoring_status(
            self.monitoring_client.send_in_exam(message="Student entered exam window")
        )

        if self.quiz_manager.has_dirty_cache():
            self.status_label.setText("Saved locally")
            QTimer.singleShot(800, lambda: self._autosave(in_background=True))
        else:
            self.status_label.setText("Synced to server")

    def _build_text_changed_handler(self, question_id: str, answer_input: QTextEdit):
        def handler() -> None:
            self.quiz_manager.set_answer(question_id, answer_input.toPlainText())
            self.status_label.setText("Saved locally")

        return handler

    def _autosave_tick(self) -> None:
        if self._submitted:
            return
        self._autosave(in_background=True)

    def _autosave_now(self) -> None:
        if self._submitted:
            return
        self._autosave(in_background=False)

    def _autosave(self, in_background: bool) -> None:
        try:
            self.quiz_manager.autosave()
            self.status_label.setText("Synced to server")
            self._set_monitoring_status(
                self.monitoring_client.send_autosave(message="Autosave completed")
            )
        except ApiClientError as exc:
            self.status_label.setText("Autosave failed, changes kept locally")
            if not in_background:
                QMessageBox.warning(self, "Autosave failed", str(exc))
        except Exception as exc:
            self.status_label.setText("Autosave failed, changes kept locally")
            if not in_background:
                QMessageBox.warning(self, "Autosave error", str(exc))

    def _submit_exam(self) -> None:
        if self._submitted:
            return
        confirm = QMessageBox.question(
            self,
            "Submit exam",
            "Are you sure you want to submit? You cannot edit answers afterwards.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.submit_button.setEnabled(False)
        self.autosave_button.setEnabled(False)
        try:
            result = self.quiz_manager.submit()
            attempt = result.get("attempt", {})
            self._submitted = True
            self.autosave_timer.stop()
            self.monitoring_timer.stop()
            self._set_editable(False)
            self._set_monitoring_status(
                self.monitoring_client.send_submitted(status="submitted", message="Exam submitted")
            )
            self.monitoring_client.clear_session()
            self.status_label.setText(
                f"Submitted successfully. Attempt status: {attempt.get('status', 'submitted')}"
            )
            QMessageBox.information(self, "Success", "Exam submitted successfully.")
        except ApiClientError as exc:
            self.status_label.setText(f"Submit failed: {exc}")
            QMessageBox.critical(self, "Submit failed", str(exc))
            self.submit_button.setEnabled(True)
            self.autosave_button.setEnabled(True)
        except Exception as exc:
            self.status_label.setText(f"Submit error: {exc}")
            QMessageBox.critical(self, "Submit error", str(exc))
            self.submit_button.setEnabled(True)
            self.autosave_button.setEnabled(True)

    def _set_editable(self, editable: bool) -> None:
        for widget in self._question_inputs.values():
            widget.setReadOnly(not editable)

    def _send_heartbeat(self) -> None:
        if self._submitted:
            return
        self._set_monitoring_status(
            self.monitoring_client.send_heartbeat(message="Heartbeat")
        )

    def _set_monitoring_status(self, ok: bool) -> None:
        if ok:
            self.monitoring_status_label.setText("Live monitoring connected")
        else:
            self.monitoring_status_label.setText("Live monitoring unavailable")

    def _set_violation_status(self, ok: bool) -> None:
        _ = ok
        self.violation_status_label.setText(self.violation_service.last_status_message)

    def _current_attempt_id(self) -> str | None:
        return self.quiz_manager.current_attempt_id

    def _trigger_test_violation(self) -> None:
        attempt_id = self._current_attempt_id()
        if not attempt_id:
            self.violation_status_label.setText("Violation reporting unavailable: attempt missing")
            return
        ok = self.violation_service.report_manual_flag(
            attempt_id,
            "Manual test violation triggered from debug control",
        )
        self._set_violation_status(ok)

    def _report_focus_lost(self) -> None:
        if self._submitted:
            return
        attempt_id = self._current_attempt_id()
        if not attempt_id:
            self.violation_status_label.setText("Violation reporting unavailable: attempt missing")
            return
        ok = self.violation_service.report_focus_lost(attempt_id)
        self._set_violation_status(ok)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.WindowDeactivate:
            self._report_focus_lost()
        return super().event(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.autosave_timer.stop()
        self.monitoring_timer.stop()
        if not self._submitted:
            self._report_focus_lost()
            self._set_monitoring_status(
                self.monitoring_client.send_disconnected(message="Exam window closed")
            )
        self.monitoring_client.clear_session()
        super().closeEvent(event)
