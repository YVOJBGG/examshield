from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.dto import StudentExam, StudentQuestion, parse_api_datetime
from app.services.network_client import NetworkClient
from app.storage.local_cache import AnswerRecord, LocalCache


class QuizManager:
    def __init__(self, network_client: NetworkClient) -> None:
        self._network_client = network_client
        self._cache = LocalCache()
        self._answers: dict[str, AnswerRecord] = {}
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

    def _default_answer_for_question(self, question: StudentQuestion) -> AnswerRecord:
        return {
            "answer_text": "",
            "selected_option_ids": [],
        }

    def _normalize_answer_record(self, question: StudentQuestion, value: Any) -> AnswerRecord:
        if isinstance(value, dict):
            answer_text = value.get("answer_text")
            selected_option_ids = value.get("selected_option_ids", [])
            normalized = {
                "answer_text": str(answer_text) if answer_text is not None else "",
                "selected_option_ids": [str(option_id) for option_id in selected_option_ids if str(option_id)],
            }
        elif isinstance(value, str):
            normalized = {
                "answer_text": value,
                "selected_option_ids": [],
            }
        else:
            normalized = self._default_answer_for_question(question)

        if self.current_exam and self.current_exam.is_mcq:
            return {
                "answer_text": "",
                "selected_option_ids": normalized["selected_option_ids"],
            }
        return {
            "answer_text": normalized["answer_text"],
            "selected_option_ids": [],
        }

    def _hydrate_answers(self, raw_answers: dict[str, Any]) -> dict[str, AnswerRecord]:
        if self.current_exam is None:
            return {}

        hydrated: dict[str, AnswerRecord] = {}
        for question in self.current_exam.questions:
            hydrated[question.id] = self._normalize_answer_record(
                question,
                raw_answers.get(question.id),
            )
        return hydrated

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
            self._answers = self._hydrate_answers(cached.answers)
            self._dirty = cached.dirty
        else:
            self._answers = self._hydrate_answers({})
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
            self._answers = self._hydrate_answers(cached_attempt.answers)
            self._dirty = cached_attempt.dirty
        else:
            self._answers = self._hydrate_answers(self._answers)
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

    def set_written_answer(self, question_id: str, text: str) -> None:
        self._answers[question_id] = {
            "answer_text": text,
            "selected_option_ids": [],
        }
        self._dirty = True
        self._persist_local()

    def get_written_answer(self, question_id: str) -> str:
        answer = self._answers.get(question_id, {})
        value = answer.get("answer_text")
        return str(value) if value is not None else ""

    def set_selected_option_ids(self, question_id: str, option_ids: list[str]) -> None:
        self._answers[question_id] = {
            "answer_text": "",
            "selected_option_ids": [str(option_id) for option_id in option_ids if str(option_id)],
        }
        self._dirty = True
        self._persist_local()

    def get_selected_option_ids(self, question_id: str) -> list[str]:
        answer = self._answers.get(question_id, {})
        selected = answer.get("selected_option_ids", [])
        if not isinstance(selected, list):
            return []
        return [str(option_id) for option_id in selected]

    def _answer_payload(self) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        if self.current_exam is None:
            return payload

        for question in self.current_exam.questions:
            answer = self._answers.get(question.id, self._default_answer_for_question(question))
            payload.append(
                {
                    "question_id": question.id,
                    "answer_text": answer.get("answer_text") or None,
                    "selected_option_ids": answer.get("selected_option_ids", []),
                }
            )
        return payload

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
