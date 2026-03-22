import uuid

from pydantic import BaseModel


class StudentQuestionOut(BaseModel):
    id: uuid.UUID
    text: str


class StudentExamListItem(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str
    time_limit_minutes: int


class StudentExamOut(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str
    time_limit_minutes: int
    questions: list[StudentQuestionOut]
