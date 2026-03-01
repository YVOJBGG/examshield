import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QuestionCreate(BaseModel):
    text: str


class QuestionUpdate(BaseModel):
    text: str | None = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_id: uuid.UUID
    text: str
    created_at: datetime
