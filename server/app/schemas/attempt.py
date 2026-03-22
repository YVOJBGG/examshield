import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ExamCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class AttemptStartRequest(BaseModel):
    exam_code: ExamCode


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    exam_id: uuid.UUID
    started_at: datetime
    submitted_at: datetime | None
    status: str
