import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttemptStartRequest(BaseModel):
    exam_id: uuid.UUID


class AttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    exam_id: uuid.UUID
    started_at: datetime
    submitted_at: datetime | None
    status: str
