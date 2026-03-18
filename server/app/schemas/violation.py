import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

NonEmptyViolationType = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ViolationCreate(BaseModel):
    attempt_id: uuid.UUID
    type: NonEmptyViolationType
    details: str | None = None


class ViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    attempt_id: uuid.UUID
    type: str
    details: str | None
    created_at: datetime


class ViolationListItem(ViolationOut):
    pass
