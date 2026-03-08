from __future__ import annotations

from app.models.dto import StudentExam
from app.services.network_client import NetworkClient
from app.storage.local_cache import LocalCache


class QuizManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._cache = LocalCache()
        self._answers: dict[str, str] = {}
        self._dirty = False
        self.current_exam: StudentExam | None = None
        self.current_exam_id: str | None = None
        self.current_attempt_id: str | None = None

    def load_exam(self, exam_id: str) -> StudentExam:
        payload = self._network_client.get_student_exam(exam_id)
        exam = StudentExam.from_json(payload)
        self.current_exam = exam
        self.current_exam_id = exam_id
        self.current_attempt_id = None
        cached = self._cache.load_latest_for_exam(exam_id)
        if cached is not None:
            self._answers = dict(cached.answers)
            self._dirty = cached.dirty
        else:
            self._answers = {}
            self._dirty = False
        return exam

    def start_attempt(self) -> str:
        if not self.current_exam_id:
            raise ValueError("Exam is not loaded")
        payload = self._network_client.start_attempt(self.current_exam_id)
        attempt_id = str(payload["id"])
        self.current_attempt_id = attempt_id

        cached_attempt = self._cache.load_attempt_cache(attempt_id)
        if cached_attempt is not None:
            self._answers = dict(cached_attempt.answers)
            self._dirty = cached_attempt.dirty
        else:
            self._cache.save_attempt_cache(
                attempt_id=attempt_id,
                exam_id=self.current_exam_id,
                answers=self._answers,
                dirty=self._dirty,
            )
            self._cache.save_exam_cache(
                exam_id=self.current_exam_id,
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
        if not self.current_exam_id:
            return
        self._cache.save_exam_cache(
            exam_id=self.current_exam_id,
            answers=self._answers,
            dirty=self._dirty,
        )
        if self.current_attempt_id:
            self._cache.save_attempt_cache(
                attempt_id=self.current_attempt_id,
                exam_id=self.current_exam_id,
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
        if not self.current_attempt_id or not self.current_exam_id:
            raise ValueError("Attempt is not started")
        try:
            response = self._network_client.submit_answers(
                self.current_attempt_id,
                self._answer_payload(),
            )
            self._dirty = False
            self._cache.archive_attempt_cache(self.current_attempt_id)
            self._cache.clear_exam_cache(self.current_exam_id)
            return response
        except Exception:
            self._dirty = True
            self._persist_local()
            raise
