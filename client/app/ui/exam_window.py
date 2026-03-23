from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import QEvent, QTimer, pyqtSignal
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
from app.services.shortcut_detection_service import ShortcutDetectionService
from app.services.screenshot_service import ScreenshotService
from app.services.violation_service import ViolationService


class ExamWindow(QWidget):
    shortcut_violation_detected = pyqtSignal(str, str)

    def __init__(
        self,
        on_session_finished: Callable[[str | None], None],
        quiz_manager: QuizManager,
        monitoring_client: MonitoringClient,
        screenshot_service: ScreenshotService,
        violation_service: ViolationService,
        autosave_interval_ms: int = 25000,
        screenshot_interval_ms: int = 45000,
    ) -> None:
        super().__init__()
        self.on_session_finished = on_session_finished
        self.quiz_manager = quiz_manager
        self.monitoring_client = monitoring_client
        self.screenshot_service = screenshot_service
        self.violation_service = violation_service
        self.autosave_interval_ms = autosave_interval_ms
        self.screenshot_interval_ms = screenshot_interval_ms
        self._question_inputs: dict[str, QTextEdit] = {}
        self._submitted = False
        self._ending_session = False
        self._post_close_message: str | None = None
        self._shortcut_detection_service = ShortcutDetectionService(self.shortcut_violation_detected.emit)
        self.shortcut_violation_detected.connect(self._report_shortcut_violation)

        exam = self.quiz_manager.current_exam
        if exam is None:
            raise ValueError("Exam data is missing.")
        if self.quiz_manager.current_attempt_started_at is None:
            raise ValueError("Attempt start time is missing.")

        self.setWindowTitle("ExamShield Student Exam")
        self.resize(820, 650)

        self.title_label = QLabel(f"Exam: {exam.title}")
        self.exam_id_label = QLabel(f"Exam ID: {exam.exam_code}")
        self.time_limit_label = QLabel(f"Time limit: {exam.time_limit_minutes} minutes")
        self.timer_label = QLabel("Time remaining: --:--")
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
        layout.addWidget(self.exam_id_label)
        layout.addWidget(self.time_limit_label)
        layout.addWidget(self.timer_label)
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

        self.screenshot_timer = QTimer(self)
        self.screenshot_timer.setInterval(self.screenshot_interval_ms)
        self.screenshot_timer.timeout.connect(self._capture_screenshot)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._update_countdown)
        self.countdown_timer.start()

        self._set_monitoring_status(
            self.monitoring_client.send_in_exam(message="Student entered exam window")
        )
        attempt_id = self._current_attempt_id()
        if attempt_id and self.screenshot_interval_ms > 0:
            self.screenshot_service.start(attempt_id)
            self.screenshot_timer.start()
        self._shortcut_detection_service.start()
        self._update_countdown()

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
        if self._submitted or self._ending_session:
            return
        self._autosave(in_background=True)

    def _autosave_now(self) -> None:
        if self._submitted or self._ending_session:
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
        if self._submitted or self._ending_session:
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
            self.screenshot_timer.stop()
            self.screenshot_service.stop()
            self._shortcut_detection_service.stop()
            self.countdown_timer.stop()
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
        if self._submitted or self._ending_session:
            return
        self._set_monitoring_status(
            self.monitoring_client.send_heartbeat(message="Heartbeat")
        )

    def _capture_screenshot(self) -> None:
        if self._submitted or self._ending_session:
            return
        self.screenshot_service.capture_and_upload_async()

    def _report_shortcut_violation(self, violation_type: str, details: str) -> None:
        if self._submitted or self._ending_session:
            return
        attempt_id = self._current_attempt_id()
        if not attempt_id:
            self.violation_status_label.setText("Violation reporting unavailable: attempt missing")
            return
        if violation_type == "desktop_switch_attempt":
            ok = self.violation_service.report_desktop_switch_attempt(attempt_id, details)
        else:
            ok = self.violation_service.report_tab_switch_attempt(attempt_id, details)
        self._set_violation_status(ok)

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
        if self._submitted or self._ending_session:
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

    def _deadline(self) -> datetime:
        assert self.quiz_manager.current_exam is not None
        assert self.quiz_manager.current_attempt_started_at is not None
        return self.quiz_manager.current_attempt_started_at + timedelta(
            minutes=self.quiz_manager.current_exam.time_limit_minutes
        )

    @staticmethod
    def _format_remaining(seconds: int) -> str:
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _update_countdown(self) -> None:
        if self._submitted or self._ending_session:
            return
        remaining_seconds = max(
            0,
            int((self._deadline() - datetime.now(timezone.utc)).total_seconds()),
        )
        self.timer_label.setText(f"Time remaining: {self._format_remaining(remaining_seconds)}")
        if remaining_seconds <= 0:
            self._handle_time_expired()

    def _handle_time_expired(self) -> None:
        if self._submitted or self._ending_session:
            return

        self._ending_session = True
        self.autosave_timer.stop()
        self.monitoring_timer.stop()
        self.screenshot_timer.stop()
        self.screenshot_service.stop()
        self._shortcut_detection_service.stop()
        self.countdown_timer.stop()
        self.submit_button.setEnabled(False)
        self.autosave_button.setEnabled(False)
        self.debug_violation_button.setEnabled(False)
        self._set_editable(False)
        self.status_label.setText("Time limit reached. Finalizing exam...")

        try:
            if self.quiz_manager.has_dirty_cache():
                try:
                    self.quiz_manager.autosave()
                except Exception:
                    pass

            result = self.quiz_manager.submit()
            attempt = result.get("attempt", {})
            self._submitted = True
            self._set_monitoring_status(
                self.monitoring_client.send_submitted(status="submitted", message="Exam auto-submitted on timeout")
            )
            self.monitoring_client.clear_session()
            self._post_close_message = (
                f"Time expired. Attempt {attempt.get('status', 'submitted')} and session ended."
            )
        except Exception:
            self.monitoring_client.clear_session()
            self._post_close_message = (
                "Time expired. Automatic submission could not be confirmed; local answers were kept when possible."
            )

        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.autosave_timer.stop()
        self.monitoring_timer.stop()
        self.screenshot_timer.stop()
        self.screenshot_service.stop()
        self._shortcut_detection_service.stop()
        self.countdown_timer.stop()
        if not self._submitted and not self._ending_session:
            self._report_focus_lost()
            self._set_monitoring_status(
                self.monitoring_client.send_disconnected(message="Exam window closed")
            )
        self.monitoring_client.clear_session()
        super().closeEvent(event)
        if self._ending_session:
            self.on_session_finished(self._post_close_message)
