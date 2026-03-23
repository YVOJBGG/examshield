import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import Attempt, Screenshot
from app.schemas.screenshot import ScreenshotListItem, ScreenshotOut

ALLOWED_SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg"}
ALLOWED_SCREENSHOT_CONTENT_TYPES = {"image/png", "image/jpeg"}


def _get_attempt_for_student(db: Session, attempt_id: uuid.UUID, user_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(
        select(Attempt)
        .options(selectinload(Attempt.user))
        .where(Attempt.id == attempt_id)
    )
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    if attempt.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Attempt does not belong to current student",
        )
    return attempt


def _get_attempt_for_admin(db: Session, attempt_id: uuid.UUID) -> Attempt:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id))
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    return attempt


def _get_screenshot_for_admin(db: Session, screenshot_id: uuid.UUID) -> Screenshot:
    screenshot = db.scalar(select(Screenshot).where(Screenshot.id == screenshot_id))
    if screenshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot not found")
    return screenshot


def _validate_upload(file: UploadFile) -> str:
    suffix = Path(file.filename or "screenshot").suffix.lower()
    if suffix not in ALLOWED_SCREENSHOT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported screenshot file type",
        )
    if file.content_type not in ALLOWED_SCREENSHOT_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported screenshot content type",
        )
    return suffix


def _build_file_url(screenshot_id: uuid.UUID) -> str:
    return f"/screenshots/{screenshot_id}/file"


def _serialize_screenshot(screenshot: Screenshot) -> ScreenshotOut:
    return ScreenshotOut(
        id=screenshot.id,
        attempt_id=screenshot.attempt_id,
        file_path=screenshot.file_path,
        captured_at=screenshot.captured_at,
        file_url=_build_file_url(screenshot.id),
    )


def _screenshots_root() -> Path:
    root = settings.screenshots_dir_path
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_screenshot_path(file_path: str) -> Path:
    root = _screenshots_root()
    candidate = (root / file_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid screenshot path") from exc
    return candidate


def create_screenshot(
    db: Session,
    *,
    user_id: uuid.UUID,
    attempt_id: uuid.UUID,
    file: UploadFile,
) -> ScreenshotOut:
    attempt = _get_attempt_for_student(db, attempt_id, user_id)
    if attempt.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attempt is not active",
        )

    suffix = _validate_upload(file)
    file_name = f"{uuid.uuid4().hex}{suffix}"
    relative_path = str(Path(str(attempt.id)) / file_name)
    destination = _resolve_screenshot_path(relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        with destination.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store screenshot",
        ) from exc
    finally:
        file.file.close()

    screenshot = Screenshot(
        attempt_id=attempt.id,
        file_path=relative_path.replace("\\", "/"),
    )
    db.add(screenshot)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record screenshot metadata",
        ) from exc
    db.refresh(screenshot)
    return _serialize_screenshot(screenshot)


def list_attempt_screenshots(db: Session, attempt_id: uuid.UUID) -> list[ScreenshotListItem]:
    _get_attempt_for_admin(db, attempt_id)
    screenshots = list(
        db.scalars(
            select(Screenshot)
            .where(Screenshot.attempt_id == attempt_id)
            .order_by(Screenshot.captured_at.asc())
        ).all()
    )
    return [ScreenshotListItem(**_serialize_screenshot(item).model_dump()) for item in screenshots]


def get_screenshot_file_path(db: Session, screenshot_id: uuid.UUID) -> tuple[Path, str]:
    screenshot = _get_screenshot_for_admin(db, screenshot_id)
    file_path = _resolve_screenshot_path(screenshot.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file not found")
    media_type, _ = mimetypes.guess_type(file_path.name)
    return file_path, media_type or "application/octet-stream"
