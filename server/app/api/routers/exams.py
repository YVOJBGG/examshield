import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate
from app.services.exams_service import create_exam, delete_exam, get_exam, list_exams, update_exam
from app.services.questions_service import (
    create_question,
    delete_question,
    get_question,
    list_questions,
    update_question,
)

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("", response_model=list[ExamOut], dependencies=[Depends(require_admin)])
def get_exams(db: Session = Depends(get_db)) -> list[ExamOut]:
    return list_exams(db)


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def post_exam(payload: ExamCreate, db: Session = Depends(get_db)) -> ExamOut:
    return create_exam(db, payload)


@router.get("/{exam_id}", response_model=ExamOut, dependencies=[Depends(require_admin)])
def get_exam_by_id(exam_id: uuid.UUID, db: Session = Depends(get_db)) -> ExamOut:
    return get_exam(db, exam_id)


@router.put("/{exam_id}", response_model=ExamOut, dependencies=[Depends(require_admin)])
def put_exam(exam_id: uuid.UUID, payload: ExamUpdate, db: Session = Depends(get_db)) -> ExamOut:
    return update_exam(db, exam_id, payload)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def remove_exam(exam_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    delete_exam(db, exam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{exam_id}/questions", response_model=list[QuestionOut], dependencies=[Depends(require_admin)])
def get_exam_questions(exam_id: uuid.UUID, db: Session = Depends(get_db)) -> list[QuestionOut]:
    return list_questions(db, exam_id)


@router.post(
    "/{exam_id}/questions",
    response_model=QuestionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def post_exam_question(exam_id: uuid.UUID, payload: QuestionCreate, db: Session = Depends(get_db)) -> QuestionOut:
    return create_question(db, exam_id, payload)


@router.get(
    "/{exam_id}/questions/{question_id}",
    response_model=QuestionOut,
    dependencies=[Depends(require_admin)],
)
def get_exam_question(exam_id: uuid.UUID, question_id: uuid.UUID, db: Session = Depends(get_db)) -> QuestionOut:
    return get_question(db, exam_id, question_id)


@router.put(
    "/{exam_id}/questions/{question_id}",
    response_model=QuestionOut,
    dependencies=[Depends(require_admin)],
)
def put_exam_question(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
) -> QuestionOut:
    return update_question(db, exam_id, question_id, payload)


@router.delete(
    "/{exam_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def remove_exam_question(exam_id: uuid.UUID, question_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    delete_question(db, exam_id, question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
