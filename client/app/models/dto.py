from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class StudentQuestion:
    id: str
    text: str

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "StudentQuestion":
        return cls(
            id=str(payload["id"]),
            text=str(payload["text"]),
        )


@dataclass(slots=True)
class StudentExam:
    id: str
    title: str
    time_limit_minutes: int
    questions: list[StudentQuestion]

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "StudentExam":
        questions = [StudentQuestion.from_json(item) for item in payload.get("questions", [])]
        return cls(
            id=str(payload["id"]),
            title=str(payload["title"]),
            time_limit_minutes=int(payload["time_limit_minutes"]),
            questions=questions,
        )
