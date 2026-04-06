import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import median

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Attempt, Exam, Question
from app.schemas.exam_analytics import (
    ExamAnalyticsMetadata,
    ExamAnalyticsResponse,
    ExamAnalyticsSummary,
    ExamEndResponse,
    HardestQuestionStat,
    HighestViolationAttemptItem,
    McqOptionDistributionItem,
    QuestionAnalyticsItem,
)

COMPLETED_ATTEMPT_STATUSES = {"submitted", "force_submitted"}
QUESTION_TIME_METHOD = "approx_saved_at_deltas"
QUESTION_ALERT_METHOD = "not_available"


def _get_exam_with_related_data(db: Session, exam_id: uuid.UUID) -> Exam:
    exam = db.scalar(
        select(Exam)
        .options(
            selectinload(Exam.questions).selectinload(Question.options),
            selectinload(Exam.attempts).selectinload(Attempt.user),
            selectinload(Exam.attempts).selectinload(Attempt.answers),
            selectinload(Exam.attempts).selectinload(Attempt.violations),
            selectinload(Exam.attempts).selectinload(Attempt.screenshots),
        )
        .where(Exam.id == exam_id)
    )
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    return exam


def end_exam(db: Session, exam_id: uuid.UUID) -> ExamEndResponse:
    exam = _get_exam_with_related_data(db, exam_id)
    ended_at = datetime.now(timezone.utc)
    updated_attempts = 0
    already_completed_attempts = 0

    for attempt in exam.attempts:
        if attempt.status == "in_progress":
            attempt.status = "force_submitted"
            if attempt.submitted_at is None:
                attempt.submitted_at = ended_at
            if exam.exam_type == "mcq":
                attempt.score = _calculate_mcq_score_for_attempt(exam, attempt)
                attempt.graded_at = attempt.submitted_at
                attempt.graded_by_user_id = None
            updated_attempts += 1
        else:
            already_completed_attempts += 1

    exam.is_ended = True
    exam.ended_at = ended_at
    db.commit()

    return ExamEndResponse(
        exam_id=exam.id,
        ended_at=ended_at,
        updated_attempts=updated_attempts,
        already_completed_attempts=already_completed_attempts,
        status="ended",
    )


def _is_meaningful_answer(answer: Answer) -> bool:
    if answer.answer_text is not None and answer.answer_text.strip() != "":
        return True
    return bool(answer.selected_option_ids)


def _round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _percentage(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) * 100.0 / float(denominator), 2)


def _duration_seconds(attempt: Attempt) -> float | None:
    if attempt.submitted_at is None:
        return None
    return max((attempt.submitted_at - attempt.started_at).total_seconds(), 0.0)


def _calculate_mcq_score_for_attempt(exam: Exam, attempt: Attempt) -> float:
    answers_by_question = {answer.question_id: answer for answer in attempt.answers}
    total = 0.0

    for question in exam.questions:
        if not question.options:
            continue
        correct_ids = {str(option.id) for option in question.options if option.is_correct}
        selected_ids = set(answers_by_question.get(question.id).selected_option_ids or []) if question.id in answers_by_question else set()
        if selected_ids == correct_ids:
            total += question.points

    return total


def _build_hardest_question_stat(
    exam: Exam,
    question_rows: list[QuestionAnalyticsItem],
) -> HardestQuestionStat | None:
    if not question_rows:
        return None

    if exam.exam_type == "mcq":
        candidates = [row for row in question_rows if row.correct_rate_percent is not None]
        if not candidates:
            return None
        hardest = min(candidates, key=lambda row: (row.correct_rate_percent or 0.0, -row.unanswered_count))
        return HardestQuestionStat(
            question_id=hardest.question_id,
            question_text=hardest.question_text,
            metric="lowest_correct_rate_percent",
            value=hardest.correct_rate_percent or 0.0,
        )

    hardest = max(
        question_rows,
        key=lambda row: (
            row.unanswered_count,
            row.average_time_spent_seconds or 0.0,
        ),
    )
    metric = "highest_unanswered_count"
    value = float(hardest.unanswered_count)
    if hardest.unanswered_count == 0 and hardest.average_time_spent_seconds is not None:
        metric = "highest_average_time_spent_seconds"
        value = hardest.average_time_spent_seconds

    return HardestQuestionStat(
        question_id=hardest.question_id,
        question_text=hardest.question_text,
        metric=metric,
        value=_round_metric(value) or 0.0,
    )


def get_exam_analytics(db: Session, exam_id: uuid.UUID) -> ExamAnalyticsResponse:
    exam = _get_exam_with_related_data(db, exam_id)
    questions = sorted(exam.questions, key=lambda item: (item.order_index, item.created_at, str(item.id)))
    attempts = sorted(exam.attempts, key=lambda item: (item.started_at, str(item.id)))
    total_attempts = len(attempts)
    completed_attempts = [attempt for attempt in attempts if attempt.status in COMPLETED_ATTEMPT_STATUSES]
    force_submitted_attempts = [attempt for attempt in attempts if attempt.status == "force_submitted"]
    durations = [duration for attempt in completed_attempts if (duration := _duration_seconds(attempt)) is not None]

    total_violations = sum(len(attempt.violations) for attempt in attempts)
    total_screenshots = sum(len(attempt.screenshots) for attempt in attempts)
    violation_counter = Counter(
        violation.type for attempt in attempts for violation in attempt.violations if violation.type
    )

    attempts_with_violation_count = [
        HighestViolationAttemptItem(
            attempt_id=attempt.id,
            username=attempt.user.username if attempt.user is not None else None,
            violation_count=len(attempt.violations),
        )
        for attempt in attempts
        if attempt.violations
    ]
    attempts_with_violation_count.sort(key=lambda item: (-item.violation_count, item.username or "", str(item.attempt_id)))

    answered_question_counts: list[int] = []
    question_answer_counts: dict[uuid.UUID, int] = defaultdict(int)
    question_answer_lengths: dict[uuid.UUID, list[int]] = defaultdict(list)
    question_time_spent: dict[uuid.UUID, list[float]] = defaultdict(list)
    question_option_counts: dict[uuid.UUID, Counter[str]] = defaultdict(Counter)

    for attempt in attempts:
        meaningful_answers = [answer for answer in attempt.answers if _is_meaningful_answer(answer)]
        answered_question_counts.append(len({answer.question_id for answer in meaningful_answers}))

        # Approximation only: the backend persists the latest answer save timestamp, not
        # full navigation history, so these deltas are based on observed saved_at ordering.
        ordered_answers = sorted(meaningful_answers, key=lambda item: (item.saved_at, str(item.question_id)))
        previous_timestamp = attempt.started_at

        for answer in ordered_answers:
            question_answer_counts[answer.question_id] += 1
            question_time_spent[answer.question_id].append(
                max((answer.saved_at - previous_timestamp).total_seconds(), 0.0)
            )
            previous_timestamp = answer.saved_at

            if answer.answer_text is not None and answer.answer_text.strip() != "":
                question_answer_lengths[answer.question_id].append(len(answer.answer_text.strip()))

            for option_id in answer.selected_option_ids or []:
                question_option_counts[answer.question_id][str(option_id)] += 1

    questions_payload: list[QuestionAnalyticsItem] = []
    for question in questions:
        total_answers = question_answer_counts[question.id]
        average_answer_length = None
        if question_answer_lengths.get(question.id):
            average_answer_length = _round_metric(
                sum(question_answer_lengths[question.id]) / len(question_answer_lengths[question.id])
            )

        mcq_option_distribution = None
        correct_rate_percent = None
        if question.options:
            option_counts = question_option_counts.get(question.id, Counter())
            mcq_option_distribution = [
                McqOptionDistributionItem(
                    option_id=option.id,
                    option_text=option.option_text,
                    count=option_counts.get(str(option.id), 0),
                    percentage=_percentage(option_counts.get(str(option.id), 0), total_answers),
                )
                for option in question.options
            ]
            if exam.exam_type == "mcq" and total_answers:
                correct_ids = {str(option.id) for option in question.options if option.is_correct}
                correct_attempt_count = 0
                for attempt in attempts:
                    answer = next((item for item in attempt.answers if item.question_id == question.id), None)
                    if answer is None or not _is_meaningful_answer(answer):
                        continue
                    if set(answer.selected_option_ids or []) == correct_ids:
                        correct_attempt_count += 1
                correct_rate_percent = _percentage(correct_attempt_count, total_answers)

        questions_payload.append(
            QuestionAnalyticsItem(
                question_id=question.id,
                question_text=question.text,
                average_time_spent_seconds=_round_metric(
                    sum(question_time_spent[question.id]) / len(question_time_spent[question.id])
                )
                if question_time_spent.get(question.id)
                else None,
                total_answers=total_answers,
                unanswered_count=max(total_attempts - total_answers, 0),
                alert_count_for_question=None,
                average_answer_length=average_answer_length,
                mcq_option_distribution=mcq_option_distribution,
                correct_rate_percent=correct_rate_percent,
            )
        )

    summary = ExamAnalyticsSummary(
        exam_id=exam.id,
        exam_title=exam.title,
        total_attempts=total_attempts,
        completed_attempts=len(completed_attempts),
        force_submitted_attempts=len(force_submitted_attempts),
        submission_rate_percent=_percentage(len(completed_attempts), total_attempts),
        average_exam_duration_seconds=_round_metric(sum(durations) / len(durations)) if durations else None,
        min_exam_duration_seconds=_round_metric(min(durations)) if durations else None,
        max_exam_duration_seconds=_round_metric(max(durations)) if durations else None,
        median_exam_duration_seconds=_round_metric(median(durations)) if durations else None,
        average_violations_per_attempt=_round_metric(total_violations / total_attempts) if total_attempts else 0.0,
        total_violations=total_violations,
        total_screenshots=total_screenshots,
        most_common_violation_type=violation_counter.most_common(1)[0][0] if violation_counter else None,
        attempts_with_highest_violation_count=attempts_with_violation_count[:5],
        average_questions_answered_per_attempt=_round_metric(
            sum(answered_question_counts) / len(answered_question_counts)
        )
        if answered_question_counts
        else 0.0,
        attempts_with_violations_percent=_percentage(
            sum(1 for attempt in attempts if attempt.violations),
            total_attempts,
        ),
        hardest_question=_build_hardest_question_stat(exam, questions_payload),
        ended_at=exam.ended_at,
        is_ended=exam.is_ended,
    )

    return ExamAnalyticsResponse(
        exam=summary,
        questions=questions_payload,
        metadata=ExamAnalyticsMetadata(
            question_time_method=QUESTION_TIME_METHOD,
            question_alert_method=QUESTION_ALERT_METHOD,
        ),
    )
