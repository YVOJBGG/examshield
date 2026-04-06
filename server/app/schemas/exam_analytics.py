import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExamEndResponse(BaseModel):
    exam_id: uuid.UUID
    ended_at: datetime
    updated_attempts: int
    already_completed_attempts: int
    status: str


class HighestViolationAttemptItem(BaseModel):
    attempt_id: uuid.UUID
    username: str | None = None
    violation_count: int


class HardestQuestionStat(BaseModel):
    question_id: uuid.UUID
    question_text: str
    metric: str
    value: float


class McqOptionDistributionItem(BaseModel):
    option_id: uuid.UUID
    option_text: str
    count: int
    percentage: float


class QuestionAnalyticsItem(BaseModel):
    question_id: uuid.UUID
    question_text: str
    average_time_spent_seconds: float | None = None
    total_answers: int
    unanswered_count: int
    alert_count_for_question: int | None = None
    average_answer_length: float | None = None
    mcq_option_distribution: list[McqOptionDistributionItem] | None = None
    correct_rate_percent: float | None = None


class ExamAnalyticsSummary(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    total_attempts: int
    completed_attempts: int
    force_submitted_attempts: int
    submission_rate_percent: float
    average_exam_duration_seconds: float | None = None
    min_exam_duration_seconds: float | None = None
    max_exam_duration_seconds: float | None = None
    median_exam_duration_seconds: float | None = None
    average_violations_per_attempt: float
    total_violations: int
    total_screenshots: int
    most_common_violation_type: str | None = None
    attempts_with_highest_violation_count: list[HighestViolationAttemptItem] = Field(default_factory=list)
    average_questions_answered_per_attempt: float
    attempts_with_violations_percent: float
    hardest_question: HardestQuestionStat | None = None
    ended_at: datetime | None = None
    is_ended: bool


class ExamAnalyticsMetadata(BaseModel):
    question_time_method: str
    question_alert_method: str


class ExamAnalyticsResponse(BaseModel):
    exam: ExamAnalyticsSummary
    questions: list[QuestionAnalyticsItem]
    metadata: ExamAnalyticsMetadata
