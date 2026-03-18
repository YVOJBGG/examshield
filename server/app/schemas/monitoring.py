import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

MonitoringEventType = Literal["connected", "in_exam", "autosave", "submitted", "disconnected"]
SnapshotEventType = Literal["connected", "in_exam", "autosave", "submitted", "disconnected", "violation"]


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
    last_event: SnapshotEventType
    last_update: datetime
    alert_count: int = 0
    has_alerts: bool = False
    last_violation_type: str | None = None
    last_violation_at: datetime | None = None


class MonitoringSnapshotEnvelope(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    attempts: list[DashboardAttemptSnapshot]


class MonitoringEventEnvelope(BaseModel):
    type: Literal["event"] = "event"
    data: MonitoringEventOut


class ViolationBroadcastOut(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    type: str
    details: str | None = None
    created_at: datetime
    username: str
    exam_id: uuid.UUID
    status: str


class ViolationEnvelope(BaseModel):
    type: Literal["violation"] = "violation"
    data: ViolationBroadcastOut
