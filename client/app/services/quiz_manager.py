from __future__ import annotations

from datetime import datetime

from app.models.dto import StudentExam, parse_api_datetime
from app.services.network_client import NetworkClient
from app.storage.local_cache import LocalCache


class QuizManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._cache = LocalCache()
        self._answers: dict[str, str] = {}
        self._dirty = False
        self.current_user_key: str | None = None
        self.current_exam: StudentExam | None = None
        self.current_exam_id: str | None = None
        self.current_exam_code: str | None = None
        self.current_attempt_id: str | None = None
        self.current_attempt_started_at: datetime | None = None

    def begin_user_session(self, username: str) -> None:
        self.current_user_key = username.strip().lower()
        self._reset_state()

    def end_session(self) -> None:
        self.current_user_key = None
        self._reset_state()

    def _reset_state(self) -> None:
        self._answers = {}
        self._dirty = False
        self.current_exam = None
        self.current_exam_id = None
        self.current_exam_code = None
        self.current_attempt_id = None
        self.current_attempt_started_at = None

    def load_exam(self, exam_code: str) -> StudentExam:
        if not self.current_user_key:
            raise ValueError("User session is not initialized")

        payload = self._network_client.get_student_exam(exam_code)
        exam = StudentExam.from_json(payload)
        self.current_exam = exam
        self.current_exam_id = exam.id
        self.current_exam_code = exam.exam_code
        self.current_attempt_id = None
        self.current_attempt_started_at = None
        cached = self._cache.load_latest_for_exam(exam.id, self.current_user_key)
        if cached is not None:
            self._answers = dict(cached.answers)
            self._dirty = cached.dirty
        else:
            self._answers = {}
            self._dirty = False
        return exam

    def start_attempt(self) -> str:
        if not self.current_exam_code or not self.current_exam_id or not self.current_user_key:
            raise ValueError("Exam is not loaded")
        payload = self._network_client.start_attempt(self.current_exam_code)
        attempt_id = str(payload["id"])
        self.current_attempt_id = attempt_id
        self.current_attempt_started_at = parse_api_datetime(str(payload["started_at"]))

        cached_attempt = self._cache.load_attempt_cache(attempt_id, self.current_user_key)
        if cached_attempt is not None:
            self._answers = dict(cached_attempt.answers)
            self._dirty = cached_attempt.dirty
        else:
            self._answers = {}
            self._dirty = False
            self._cache.save_attempt_cache(
                attempt_id=attempt_id,
                exam_id=self.current_exam_id,
                user_key=self.current_user_key,
                answers=self._answers,
                dirty=self._dirty,
            )
            self._cache.save_exam_cache(
                exam_id=self.current_exam_id,
                user_key=self.current_user_key,
                answers=self._answers,
                dirty=self._dirty,
            )
        return attempt_id

    def set_answer(self, question_id: str, text: str) -> None:
        self._answers[question_id] = text
        self._dirty = True
        self._persist_local()

    def get_answer(self, question_id: str) -> str:
        return self._answers.get(question_id, "")

    def _answer_payload(self) -> list[dict[str, str]]:
        return [
            {"question_id": question_id, "answer_text": answer_text}
            for question_id, answer_text in self._answers.items()
        ]

    def _persist_local(self) -> None:
        if not self.current_exam_id or not self.current_user_key:
            return
        self._cache.save_exam_cache(
            exam_id=self.current_exam_id,
            user_key=self.current_user_key,
            answers=self._answers,
            dirty=self._dirty,
        )
        if self.current_attempt_id:
            self._cache.save_attempt_cache(
                attempt_id=self.current_attempt_id,
                exam_id=self.current_exam_id,
                user_key=self.current_user_key,
                answers=self._answers,
                dirty=self._dirty,
            )

    def has_dirty_cache(self) -> bool:
        return self._dirty

    def autosave(self) -> list[dict]:
        if not self.current_attempt_id:
            raise ValueError("Attempt is not started")
        try:
            response = self._network_client.autosave_answers(
                self.current_attempt_id,
                self._answer_payload(),
            )
            self._dirty = False
            self._persist_local()
            return response
        except Exception:
            self._dirty = True
            self._persist_local()
            raise

    def submit(self) -> dict:
        if not self.current_attempt_id or not self.current_exam_id or not self.current_user_key:
            raise ValueError("Attempt is not started")
        try:
            response = self._network_client.submit_answers(
                self.current_attempt_id,
                self._answer_payload(),
            )
            self._dirty = False
            self._cache.archive_attempt_cache(self.current_attempt_id)
            self._cache.clear_exam_cache(self.current_exam_id, self.current_user_key)
            return response
        except Exception:
            self._dirty = True
            self._persist_local()
            raise
