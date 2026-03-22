from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.models import User
from app.schemas.attempt import AttemptOut, AttemptStartRequest
from app.services.attempts_service import start_attempt

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("/start", response_model=AttemptOut)
def post_attempt_start(
    payload: AttemptStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> AttemptOut:
    return start_attempt(db, current_user.id, payload.exam_code)
