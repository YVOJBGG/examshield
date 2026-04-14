import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import ScreenshotGallery from "../components/ScreenshotGallery";
import { PageHeader, StatCard } from "../components/ui";
import {
  ApiError,
  getExam,
  getAttemptReview,
  listExamAttempts,
  saveAttemptScore,
  type AttemptReviewAnswer,
  type AttemptReviewDetail,
  type Exam,
  type ExamAttemptListItem,
} from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function formatGradingState(state?: ExamAttemptListItem["grading_state"]): string {
  switch (state) {
    case "auto_graded":
      return "Auto-graded";
    case "manually_graded":
      return "Graded";
    case "pending_manual_grading":
      return "Pending manual grading";
    default:
      return "Pending";
  }
}

function gradingBadgeClass(state?: ExamAttemptListItem["grading_state"]): string {
  switch (state) {
    case "auto_graded":
      return "grading-pill auto";
    case "manually_graded":
      return "grading-pill graded";
    default:
      return "grading-pill pending";
  }
}

function ExamSubmissionsPage({ onAuthError }: Props) {
  const { examId } = useParams<{ examId: string }>();
  const resolvedExamId = useMemo(() => examId ?? "", [examId]);

  const [exam, setExam] = useState<Exam | null>(null);
  const [attempts, setAttempts] = useState<ExamAttemptListItem[]>([]);
  const [selectedAttemptId, setSelectedAttemptId] = useState<string | null>(null);
  const [attemptDetail, setAttemptDetail] = useState<AttemptReviewDetail | null>(null);
  const [scoreInput, setScoreInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadAttempts() {
    if (!resolvedExamId) {
      setError("Missing exam id.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [examData, attemptsData] = await Promise.all([
        getExam(resolvedExamId),
        listExamAttempts(resolvedExamId),
      ]);
      setExam(examData);
      setAttempts(attemptsData);
      if (attemptsData.length > 0) {
        setSelectedAttemptId((current) => current ?? attemptsData[0].attempt_id);
      } else {
        setSelectedAttemptId(null);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load submissions";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAttempts();
  }, [resolvedExamId]);

  useEffect(() => {
    if (!selectedAttemptId) {
      setAttemptDetail(null);
      setScoreInput("");
      setDetailError(null);
      return;
    }

    let cancelled = false;
    setDetailLoading(true);
    setDetailError(null);
    setSuccessMessage(null);

    void getAttemptReview(selectedAttemptId)
      .then((detail) => {
        if (cancelled) {
          return;
        }
        setAttemptDetail(detail);
        setScoreInput(detail.score == null ? "" : String(detail.score));
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Could not load attempt detail";
        setDetailError(message);
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setDetailLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedAttemptId]);

  async function onSaveScore() {
    if (!selectedAttemptId || !attemptDetail) {
      return;
    }

    const parsedScore = Number(scoreInput);
    if (scoreInput.trim() === "" || Number.isNaN(parsedScore) || parsedScore < 0) {
      setDetailError("Score must be a non-negative number.");
      return;
    }

    setSaving(true);
    setDetailError(null);
    setSuccessMessage(null);
    try {
      const updated = await saveAttemptScore(selectedAttemptId, parsedScore);
      setAttemptDetail((prev) =>
        prev
          ? {
              ...prev,
              score: updated.score ?? null,
              graded_at: updated.graded_at ?? null,
              grading_state: "manually_graded",
            }
          : prev,
      );
      setAttempts((prev) =>
        prev.map((item) =>
          item.attempt_id === selectedAttemptId
            ? { ...item, score: updated.score ?? null, grading_state: "manually_graded" }
            : item,
        ),
      );
      setSuccessMessage("Score saved successfully.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not save score";
      setDetailError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setSaving(false);
    }
  }

  function renderMcqAnswer(answer: AttemptReviewAnswer) {
    const selectedIds = new Set(answer.selected_option_ids ?? []);

    return (
      <div className="review-option-list">
        {(answer.options ?? []).map((option) => (
          <div
            key={option.id}
            className={[
              "review-option-item",
              option.is_correct ? "correct" : "",
              selectedIds.has(option.id) ? "selected" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <div>
              <strong>{option.option_text}</strong>
              <p>
                {selectedIds.has(option.id) ? "Selected by student" : "Not selected"}
                {option.is_correct ? " • Correct answer" : ""}
              </p>
            </div>
            {selectedIds.has(option.id) && !option.is_correct ? (
              <span className="neutral-badge">Chosen</span>
            ) : null}
            {option.is_correct ? <span className="status-pill">Correct</span> : null}
          </div>
        ))}
      </div>
    );
  }

  function renderWrittenAnswer(answer: AttemptReviewAnswer) {
    return <p>{answer.answer_text?.trim() ? answer.answer_text : "No answer submitted."}</p>;
  }

  return (
    <section className="page-section">
      <PageHeader
        backLink={
          <Link to="/" className="back-link">
            Back to exams
          </Link>
        }
        eyebrow="Submission Review"
        title={exam ? exam.title : "Submitted attempts"}
        description="Review submitted work, inspect answers question by question, and complete grading with a clear distinction between auto-graded MCQ and manually graded written attempts."
      />

      {exam && (
        <div className="stats-grid">
          <StatCard label="Exam ID" value={<span className="mono">{exam.exam_code}</span>} description="Student-facing access code for this assessment." />
          <StatCard
            label="Exam type"
            value={exam.exam_type === "mcq" ? "MCQ" : "Written"}
            description="Determines whether grading is automatic or manual after submission."
          />
          <StatCard
            label="Submitted attempts"
            value={attempts.length}
            description="Completed attempts available for review right now."
          />
          <StatCard
            label="Selected score"
            value={attemptDetail?.score == null ? "Not graded" : attemptDetail.score}
            description="Current persisted score for the selected attempt."
          />
        </div>
      )}

      {error && <p className="error">Error: {error}</p>}

      {loading ? (
        <section className="panel">
          <p className="state-text">Loading submissions...</p>
        </section>
      ) : (
        <div className="review-layout">
          <section className="panel review-attempts-panel">
            <div className="section-heading">
              <div>
                <h3>Submitted attempts</h3>
                <p>Select a row to open the full review panel.</p>
              </div>
            </div>

            {attempts.length === 0 ? (
              <p className="state-text">No submitted attempts yet.</p>
            ) : (
              <div className="table-scroll">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Status</th>
                      <th>Submitted</th>
                      <th>Score</th>
                      <th>Grading</th>
                      <th>Review</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attempts.map((attempt) => (
                      <tr
                        key={attempt.attempt_id}
                        className={selectedAttemptId === attempt.attempt_id ? "attempt-row-selected" : ""}
                      >
                        <td>
                          <strong>{attempt.username}</strong>
                        </td>
                        <td>
                          <span className="status-pill">{attempt.status}</span>
                        </td>
                        <td>{formatTimestamp(attempt.submitted_at)}</td>
                        <td>{attempt.score == null ? "Not graded yet" : attempt.score}</td>
                        <td>
                          <span className={gradingBadgeClass(attempt.grading_state)}>
                            {formatGradingState(attempt.grading_state)}
                          </span>
                        </td>
                        <td>
                          <button type="button" onClick={() => setSelectedAttemptId(attempt.attempt_id)}>
                            Review
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <aside className="panel review-detail-panel">
            <div className="section-heading">
              <div>
                <h3>Attempt review</h3>
                <p>
                  {attemptDetail?.exam.exam_type === "mcq"
                    ? "MCQ attempts show selected vs correct answers with automatic scoring."
                    : "Written attempts stay answer-by-answer with an overall grading action."}
                </p>
              </div>
            </div>
            {!selectedAttemptId && <p className="state-text">Select a submitted attempt to review.</p>}
            {detailLoading && <p className="state-text">Loading attempt details...</p>}
            {detailError && <p className="error">Error: {detailError}</p>}
            {successMessage && <p className="success-text">{successMessage}</p>}

            {!detailLoading && attemptDetail && (
              <>
                <div className="review-meta-card">
                  <div className="review-meta">
                    <p>
                      <span>Student</span>
                      <strong>{attemptDetail.student.username}</strong>
                    </p>
                    <p>
                      <span>Exam</span>
                      <strong>{attemptDetail.exam.title}</strong>
                    </p>
                    <p>
                      <span>Exam type</span>
                      <strong>{attemptDetail.exam.exam_type === "mcq" ? "MCQ" : "Written"}</strong>
                    </p>
                    <p>
                      <span>Grading state</span>
                      <strong>{formatGradingState(attemptDetail.grading_state)}</strong>
                    </p>
                    <p>
                      <span>Started</span>
                      <strong>{formatTimestamp(attemptDetail.started_at)}</strong>
                    </p>
                    <p>
                      <span>Submitted</span>
                      <strong>{formatTimestamp(attemptDetail.submitted_at)}</strong>
                    </p>
                    <p>
                      <span>Score</span>
                      <strong>{attemptDetail.score == null ? "Not graded yet" : attemptDetail.score}</strong>
                    </p>
                    <p>
                      <span>Graded at</span>
                      <strong>{formatTimestamp(attemptDetail.graded_at)}</strong>
                    </p>
                  </div>
                </div>

                {attemptDetail.exam.instructions ? (
                  <div className="review-notice-card">
                    <h4>Exam instructions</h4>
                    <p>{attemptDetail.exam.instructions}</p>
                  </div>
                ) : null}

                {attemptDetail.exam.exam_type === "written" ? (
                  <div className="score-form">
                    <label htmlFor="attempt-score">Overall score</label>
                    <input
                      id="attempt-score"
                      type="number"
                      min={0}
                      step="0.5"
                      value={scoreInput}
                      onChange={(event) => setScoreInput(event.target.value)}
                      placeholder="Enter score"
                    />
                    <button type="button" onClick={() => void onSaveScore()} disabled={saving}>
                      {saving ? "Saving..." : "Save Grade"}
                    </button>
                  </div>
                ) : (
                  <div className="review-notice-card auto-grade-card">
                    <h4>Automatic grading</h4>
                    <p>
                      This MCQ attempt was graded automatically on submission. Review details below
                      show the selected answer, the correct option, and awarded points per question.
                    </p>
                  </div>
                )}

                <div className="review-answers">
                  {attemptDetail.answers.map((answer, index) => (
                    <article key={answer.question_id} className="question-item review-answer-card">
                      <div className="question-item-header">
                        <span className="status-pill">Question {index + 1}</span>
                        <span className="neutral-badge">{answer.points} pts</span>
                      </div>
                      <strong>{answer.question_text}</strong>

                      {attemptDetail.exam.exam_type === "mcq" ? renderMcqAnswer(answer) : renderWrittenAnswer(answer)}

                      {attemptDetail.exam.exam_type === "mcq" ? (
                        <div className="answer-outcome-row">
                          <span className={answer.is_correct ? "availability-pill available" : "availability-pill unavailable"}>
                            {answer.is_correct ? "Correct" : "Incorrect"}
                          </span>
                          <span className="neutral-badge">
                            Awarded: {answer.awarded_points ?? 0} / {answer.points}
                          </span>
                        </div>
                      ) : null}
                    </article>
                  ))}
                </div>

                <ScreenshotGallery
                  attemptId={attemptDetail.attempt_id}
                  title="Screenshot timeline"
                  description="Captured screenshots are shown newest first for quick post-exam review."
                  onAuthError={onAuthError}
                />
              </>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}

export default ExamSubmissionsPage;
