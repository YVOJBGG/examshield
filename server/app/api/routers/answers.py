from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.models import User
from app.schemas.answer import (
    AnswerAutosaveRequest,
    AnswerOut,
    AnswerSubmitRequest,
    SubmitResultOut,
)
from app.services.answers_service import autosave_answers, submit_answers

router = APIRouter(prefix="/answers", tags=["answers"])


@router.post("/autosave", response_model=list[AnswerOut])
def post_answers_autosave(
    payload: AnswerAutosaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> list[AnswerOut]:
    return autosave_answers(db, current_user.id, payload.attempt_id, payload.answers)


@router.post("/submit", response_model=SubmitResultOut)
def post_answers_submit(
    payload: AnswerSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> SubmitResultOut:
    attempt, answers_saved = submit_answers(db, current_user.id, payload.attempt_id, payload.answers)
    return SubmitResultOut(attempt=attempt, answers_saved=answers_saved)
