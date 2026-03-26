import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


GradingState = Literal["pending_manual_grading", "manually_graded", "auto_graded"]


class AttemptReviewListItem(BaseModel):
    attempt_id: uuid.UUID
    username: str
    status: str
    started_at: datetime
    submitted_at: datetime | None
    score: float | None
    grading_state: GradingState


class AttemptReviewStudent(BaseModel):
    id: uuid.UUID
    username: str


class AttemptReviewExam(BaseModel):
    id: uuid.UUID
    exam_code: str
    title: str
    exam_type: Literal["mcq", "written"]
    instructions: str | None


class AttemptReviewOptionItem(BaseModel):
    id: uuid.UUID
    option_text: str
    order_index: int
    is_correct: bool


class AttemptReviewAnswerItem(BaseModel):
    question_id: uuid.UUID
    question_text: str
    points: float
    order_index: int
    answer_text: str | None = None
    selected_option_ids: list[uuid.UUID] = Field(default_factory=list)
    options: list[AttemptReviewOptionItem] = Field(default_factory=list)
    is_correct: bool | None = None
    awarded_points: float | None = None


class AttemptReviewDetail(BaseModel):
    attempt_id: uuid.UUID
    status: str
    started_at: datetime
    submitted_at: datetime | None
    score: float | None
    graded_at: datetime | None
    grading_state: GradingState
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
