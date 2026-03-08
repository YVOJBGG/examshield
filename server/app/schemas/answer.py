import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.attempt import AttemptOut


class AnswerAutosaveItem(BaseModel):
    question_id: uuid.UUID
    answer_text: str


class AnswerAutosaveRequest(BaseModel):
    attempt_id: uuid.UUID
    answers: list[AnswerAutosaveItem] = Field(default_factory=list)


class AnswerSubmitRequest(BaseModel):
    attempt_id: uuid.UUID
    answers: list[AnswerAutosaveItem] = Field(default_factory=list)


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str
    saved_at: datetime


class SubmitResultOut(BaseModel):
    attempt: AttemptOut
    answers_saved: int
