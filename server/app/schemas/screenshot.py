import uuid
from datetime import datetime

from pydantic import BaseModel


class ScreenshotOut(BaseModel):
    id: uuid.UUID
    attempt_id: uuid.UUID
    file_path: str
    captured_at: datetime
    file_url: str


class ScreenshotListItem(ScreenshotOut):
    pass
