import uuid
from typing import Literal

from pydantic import BaseModel


class StudentQuestionOptionOut(BaseModel):
    id: uuid.UUID
    option_text: str
    order_index: int


class StudentQuestionOut(BaseModel):
    id: uuid.UUID
    text: str
    points: float
    order_index: int
    options: list[StudentQuestionOptionOut] = []


class StudentExamListItem(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str
    exam_type: Literal["mcq", "written"]
    time_limit_minutes: int


class StudentExamOut(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str
    exam_type: Literal["mcq", "written"]
    time_limit_minutes: int
    instructions: str | None
    questions: list[StudentQuestionOut]
