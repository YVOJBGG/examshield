import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionOptionCreate(BaseModel):
    option_text: str
    is_correct: bool = False
    order_index: int | None = None


class QuestionOptionUpdate(BaseModel):
    option_text: str | None = None
    is_correct: bool | None = None
    order_index: int | None = None


class QuestionOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question_id: uuid.UUID
    option_text: str
    is_correct: bool
    order_index: int


class QuestionCreate(BaseModel):
    text: str
    points: float = 1.0
    order_index: int | None = None
    options: list[QuestionOptionCreate] = Field(default_factory=list)


class QuestionUpdate(BaseModel):
    text: str | None = None
    points: float | None = None
    order_index: int | None = None
    options: list[QuestionOptionCreate] | None = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_id: uuid.UUID
    text: str
    points: float
    order_index: int
    options: list[QuestionOptionOut]
    created_at: datetime
