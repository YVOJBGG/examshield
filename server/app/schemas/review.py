import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AttemptReviewListItem(BaseModel):
    attempt_id: uuid.UUID
    username: str
    status: str
    started_at: datetime
    submitted_at: datetime | None
    score: float | None


class AttemptReviewStudent(BaseModel):
    id: uuid.UUID
    username: str


class AttemptReviewExam(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str


class AttemptReviewAnswerItem(BaseModel):
    question_id: uuid.UUID
    question_text: str
    answer_text: str | None = None


class AttemptReviewDetail(BaseModel):
    attempt_id: uuid.UUID
    status: str
    started_at: datetime
    submitted_at: datetime | None
    score: float | None
    graded_at: datetime | None
    student: AttemptReviewStudent
    exam: AttemptReviewExam
    answers: list[AttemptReviewAnswerItem]


class AttemptScoreUpdate(BaseModel):
    score: float = Field(ge=0)


class AttemptScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    submitted_at: datetime | None
    score: float | None
    graded_at: datetime | None
