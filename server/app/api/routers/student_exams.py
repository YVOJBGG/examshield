from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.models import User
from app.schemas.student_exam import (
    StudentExamListItem,
    StudentExamOut,
    StudentQuestionOptionOut,
    StudentQuestionOut,
)
from app.services.attempts_service import get_student_exam_content, list_student_exams

router = APIRouter(prefix="/student/exams", tags=["student-exams"])


@router.get("", response_model=list[StudentExamListItem])
def get_student_exams(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_student),
) -> list[StudentExamListItem]:
    exams = list_student_exams(db)
    return [
        StudentExamListItem(
            id=exam.id,
            exam_code=exam.exam_code,
            title=exam.title,
            exam_type=exam.exam_type,
            time_limit_minutes=exam.time_limit_minutes,
        )
        for exam in exams
    ]


@router.get("/{exam_code}", response_model=StudentExamOut)
def get_student_exam(
    exam_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student),
) -> StudentExamOut:
    exam, questions = get_student_exam_content(db, current_user.id, exam_code.strip())
    question_items = [
        StudentQuestionOut(
            id=question.id,
            text=question.text,
            points=question.points,
            order_index=question.order_index,
            options=[
                StudentQuestionOptionOut(
                    id=option.id,
                    option_text=option.option_text,
                    order_index=option.order_index,
                )
                for option in question.options
            ],
        )
        for question in questions
    ]
    return StudentExamOut(
        id=exam.id,
        exam_code=exam.exam_code,
        title=exam.title,
        exam_type=exam.exam_type,
        time_limit_minutes=exam.time_limit_minutes,
        instructions=exam.instructions,
        questions=question_items,
    )
