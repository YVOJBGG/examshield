import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ExamCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class ExamCreate(BaseModel):
    title: str
    time_limit_minutes: int


class ExamUpdate(BaseModel):
    title: str | None = None
    time_limit_minutes: int | None = None


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    exam_code: str
    title: str
    time_limit_minutes: int
    created_at: datetime
