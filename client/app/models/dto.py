from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class StudentQuestionOption:
    id: str
    option_text: str
    order_index: int

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "StudentQuestionOption":
        return cls(
            id=str(payload["id"]),
            option_text=str(payload["option_text"]),
            order_index=int(payload.get("order_index", 0)),
        )


@dataclass(slots=True)
class StudentQuestion:
    id: str
    text: str
    points: float
    order_index: int
    options: list[StudentQuestionOption]

    @property
    def is_mcq(self) -> bool:
        return len(self.options) > 0

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "StudentQuestion":
        return cls(
            id=str(payload["id"]),
            text=str(payload["text"]),
            points=float(payload.get("points", 1)),
            order_index=int(payload.get("order_index", 0)),
            options=[
                StudentQuestionOption.from_json(item)
                for item in payload.get("options", [])
            ],
        )


@dataclass(slots=True)
class StudentExam:
    id: str
    exam_code: str
    title: str
    exam_type: str
    time_limit_minutes: int
    instructions: str | None
    questions: list[StudentQuestion]

    @property
    def is_mcq(self) -> bool:
        return self.exam_type == "mcq"

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "StudentExam":
        questions = [StudentQuestion.from_json(item) for item in payload.get("questions", [])]
        return cls(
            id=str(payload["id"]),
            exam_code=str(payload["exam_code"]),
            title=str(payload["title"]),
            exam_type=str(payload.get("exam_type", "written")),
            time_limit_minutes=int(payload["time_limit_minutes"]),
            instructions=str(payload["instructions"]) if payload.get("instructions") is not None else None,
            questions=questions,
        )


def parse_api_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
