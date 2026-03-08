from __future__ import annotations

from PyQt6.QtCore import QTimer
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

from app.services.network_client import ApiClientError
from app.services.quiz_manager import QuizManager


class ExamWindow(QWidget):
    def __init__(self, quiz_manager: QuizManager, autosave_interval_ms: int = 25000) -> None:
        super().__init__()
        self.quiz_manager = quiz_manager
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
        self.status_label = QLabel("Attempt started. Autosave is enabled.")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        for index, question in enumerate(exam.questions, start=1):
            question_label = QLabel(f"Q{index}. {question.text}")
            question_label.setWordWrap(True)
            answer_input = QTextEdit()
            answer_input.setPlaceholderText("Type your answer here...")
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

        button_row = QHBoxLayout()
        button_row.addWidget(self.autosave_button)
        button_row.addWidget(self.submit_button)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.time_limit_label)
        layout.addWidget(scroll_area)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(self.autosave_interval_ms)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

    def _build_text_changed_handler(self, question_id: str, answer_input: QTextEdit):
        def handler() -> None:
            self.quiz_manager.set_answer(question_id, answer_input.toPlainText())

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
            if not in_background:
                self.status_label.setText("Autosave successful.")
        except ApiClientError as exc:
            self.status_label.setText(f"Autosave failed: {exc}")
            if not in_background:
                QMessageBox.warning(self, "Autosave failed", str(exc))
        except Exception as exc:
            self.status_label.setText(f"Autosave error: {exc}")
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
            self._set_editable(False)
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
