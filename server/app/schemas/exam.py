import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.schemas.question import QuestionOut

ExamCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
ExamType = Literal["mcq", "written"]


class ExamCreate(BaseModel):
    title: str
    exam_type: ExamType
    time_limit_minutes: int
    instructions: str | None = None
    is_available: bool = True


class ExamUpdate(BaseModel):
    title: str | None = None
    exam_type: ExamType | None = None
    time_limit_minutes: int | None = None
    instructions: str | None = None
    is_available: bool | None = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_code: str
    title: str
    exam_type: ExamType
    time_limit_minutes: int
    instructions: str | None
    is_available: bool
    created_at: datetime


class ExamDetailOut(ExamOut):
    questions: list[QuestionOut]
