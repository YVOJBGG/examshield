import uuid

from pydantic import BaseModel


class StudentQuestionOut(BaseModel):
    id: uuid.UUID
    text: str


class StudentExamOut(BaseModel):
    id: uuid.UUID
    title: str
    time_limit_minutes: int
    questions: list[StudentQuestionOut]
