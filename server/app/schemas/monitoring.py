import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

MonitoringEventType = Literal["connected", "in_exam", "autosave", "submitted", "disconnected"]


class MonitoringStatusIn(BaseModel):
    event_type: MonitoringEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exam_id: uuid.UUID
    attempt_id: uuid.UUID
    status: str
    message: str | None = None


class MonitoringEventOut(BaseModel):
    event_type: MonitoringEventType
    timestamp: datetime
    user_id: uuid.UUID
    username: str
    exam_id: uuid.UUID
    attempt_id: uuid.UUID
    status: str
    message: str | None = None


class DashboardAttemptSnapshot(BaseModel):
    attempt_id: uuid.UUID
    username: str
    exam_id: uuid.UUID
    status: str
    last_event: MonitoringEventType
    last_update: datetime


class MonitoringSnapshotEnvelope(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    attempts: list[DashboardAttemptSnapshot]


class MonitoringEventEnvelope(BaseModel):
    type: Literal["event"] = "event"
    data: MonitoringEventOut
