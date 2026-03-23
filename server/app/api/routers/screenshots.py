import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_student
from app.db.session import get_db
from app.models import User
from app.schemas.screenshot import ScreenshotListItem, ScreenshotOut
from app.services.screenshots_service import (
    create_screenshot,
    get_screenshot_file_path,
    list_attempt_screenshots,
)

router = APIRouter(prefix="/screenshots", tags=["screenshots"])


@router.post("/upload", response_model=ScreenshotOut, status_code=status.HTTP_201_CREATED)
def upload_screenshot(
    attempt_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> ScreenshotOut:
    return create_screenshot(
        db,
        user_id=current_user.id,
        attempt_id=attempt_id,
        file=file,
    )


@router.get("/attempt/{attempt_id}", response_model=list[ScreenshotListItem])
def get_attempt_screenshots(
    attempt_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> list[ScreenshotListItem]:
    return list_attempt_screenshots(db, attempt_id)


@router.get("/{screenshot_id}/file")
def get_screenshot_file(
    screenshot_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin),
) -> FileResponse:
    file_path, media_type = get_screenshot_file_path(db, screenshot_id)
    return FileResponse(path=file_path, media_type=media_type, filename=file_path.name)
