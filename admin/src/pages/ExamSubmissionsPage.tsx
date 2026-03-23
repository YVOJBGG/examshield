import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import ScreenshotGallery from "../components/ScreenshotGallery";
import {
  ApiError,
  getExam,
  getAttemptReview,
  listExamAttempts,
  saveAttemptScore,
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
            }
          : prev,
      );
      setAttempts((prev) =>
        prev.map((item) =>
          item.attempt_id === selectedAttemptId ? { ...item, score: updated.score ?? null } : item,
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

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <Link to={`/exams/${resolvedExamId}`} className="back-link">
            Back to exam
          </Link>
          <span className="eyebrow">Submission Review</span>
          <h2>{exam ? exam.title : "Submitted attempts"}</h2>
          <p className="page-intro">
            Review submitted work, inspect answers question by question, and record a final score.
          </p>
        </div>
      </div>

      {exam && (
        <div className="stats-grid">
          <article className="stat-card">
            <span className="stat-label">Exam ID</span>
            <strong className="mono">{exam.exam_code}</strong>
            <p>Shareable student access code for this exam.</p>
          </article>
          <article className="stat-card">
            <span className="stat-label">Submitted attempts</span>
            <strong>{attempts.length}</strong>
            <p>Completed attempts available for review right now.</p>
          </article>
          <article className="stat-card">
            <span className="stat-label">Selected score</span>
            <strong>{attemptDetail?.score == null ? "Not graded" : attemptDetail.score}</strong>
            <p>Overall score stored for the currently selected attempt.</p>
          </article>
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
                <p>Select a student to open the grading panel.</p>
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
                <p>Read answers in context and save one overall score.</p>
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
                      <span>Status</span>
                      <strong>{attemptDetail.status}</strong>
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
                      <span>Current score</span>
                      <strong>{attemptDetail.score == null ? "Not graded yet" : attemptDetail.score}</strong>
                    </p>
                    <p>
                      <span>Graded at</span>
                      <strong>{formatTimestamp(attemptDetail.graded_at)}</strong>
                    </p>
                  </div>
                </div>

                <div className="score-form">
                  <label htmlFor="attempt-score">Score</label>
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
                    {saving ? "Saving..." : "Save Score"}
                  </button>
                </div>

                <div className="review-answers">
                  {attemptDetail.answers.map((answer, index) => (
                    <article key={answer.question_id} className="question-item">
                      <div className="question-item-header">
                        <span className="status-pill">Question {index + 1}</span>
                      </div>
                      <strong>{answer.question_text}</strong>
                      <p>{answer.answer_text?.trim() ? answer.answer_text : "No answer submitted."}</p>
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
