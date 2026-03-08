from __future__ import annotations

from app.models.dto import StudentExam
from app.services.network_client import NetworkClient
from app.storage.local_cache import LocalCache


class QuizManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._cache = LocalCache()
        self.current_exam: StudentExam | None = None
        self.current_exam_id: str | None = None
        self.current_attempt_id: str | None = None

    def load_exam(self, exam_id: str) -> StudentExam:
        payload = self._network_client.get_student_exam(exam_id)
        exam = StudentExam.from_json(payload)
        self.current_exam = exam
        self.current_exam_id = exam_id
        self._cache.clear()
        self.current_attempt_id = None
        return exam

    def start_attempt(self) -> str:
        if not self.current_exam_id:
            raise ValueError("Exam is not loaded")
        payload = self._network_client.start_attempt(self.current_exam_id)
        attempt_id = str(payload["id"])
        self.current_attempt_id = attempt_id
        return attempt_id

    def set_answer(self, question_id: str, text: str) -> None:
        self._cache.set_answer(question_id, text)

    def get_answer(self, question_id: str) -> str:
        return self._cache.get_answer(question_id)

    def _answer_payload(self) -> list[dict[str, str]]:
        return [
            {"question_id": question_id, "answer_text": answer_text}
            for question_id, answer_text in self._cache.all_answers().items()
        ]

    def autosave(self) -> list[dict]:
        if not self.current_attempt_id:
            raise ValueError("Attempt is not started")
        return self._network_client.autosave_answers(self.current_attempt_id, self._answer_payload())

    def submit(self) -> dict:
        if not self.current_attempt_id:
            raise ValueError("Attempt is not started")
        return self._network_client.submit_answers(self.current_attempt_id, self._answer_payload())
