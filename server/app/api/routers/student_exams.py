import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.models import User
from app.schemas.student_exam import StudentExamOut, StudentQuestionOut
from app.services.attempts_service import get_student_exam_content

router = APIRouter(prefix="/student/exams", tags=["student-exams"])


@router.get("/{exam_id}", response_model=StudentExamOut)
def get_student_exam(
    exam_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_student),
) -> StudentExamOut:
    exam, questions = get_student_exam_content(db, exam_id)
    question_items = [StudentQuestionOut(id=question.id, text=question.text) for question in questions]
    return StudentExamOut(
        id=exam.id,
        title=exam.title,
        time_limit_minutes=exam.time_limit_minutes,
        questions=question_items,
    )
