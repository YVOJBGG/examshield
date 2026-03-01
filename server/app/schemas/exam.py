import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExamCreate(BaseModel):
    title: str
    time_limit_minutes: int


class ExamUpdate(BaseModel):
    title: str | None = None
    time_limit_minutes: int | None = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    time_limit_minutes: int
    created_at: datetime
