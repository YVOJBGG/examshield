import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiError, getExam, getExamAnalytics, type Exam, type ExamAnalyticsResponse } from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

type LocationState = {
  successMessage?: string;
};

function formatNumber(value?: number | null, digits = 2): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(digits).replace(/\.00$/, "");
}

function formatPercent(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return `${formatNumber(value)}%`;
}

function formatDuration(value?: number | null): string {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }

  if (value < 60) {
    return `${Math.round(value)} sec`;
  }

  const minutes = value / 60;
  return `${formatNumber(minutes)} min`;
}

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

function humanizeMetric(metric?: string): string {
  switch (metric) {
    case "lowest_correct_rate_percent":
      return "Lowest correct rate";
    case "highest_unanswered_count":
      return "Highest unanswered count";
    case "highest_average_time_spent_seconds":
      return "Highest average time";
    default:
      return metric ?? "-";
  }
}

function ExamAnalyticsPage({ onAuthError }: Props) {
  const { examId } = useParams<{ examId: string }>();
  const location = useLocation();
  const resolvedExamId = useMemo(() => examId ?? "", [examId]);
  const locationState = location.state as LocationState | null;

  const [exam, setExam] = useState<Exam | null>(null);
  const [analytics, setAnalytics] = useState<ExamAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!resolvedExamId) {
      setError("Missing exam id.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    void Promise.all([getExam(resolvedExamId), getExamAnalytics(resolvedExamId)])
      .then(([examData, analyticsData]) => {
        if (cancelled) {
          return;
        }
        setExam(examData);
        setAnalytics(analyticsData);
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Could not load exam analytics";
        setError(message);
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [resolvedExamId, onAuthError]);

  return (
    <section className="page-section">
      <div className="page-header">
        <div className="page-heading-block">
          <Link to="/" className="back-link">
            Back to exams
          </Link>
          <span className="eyebrow">Exam Analytics</span>
          <h2>{exam ? `${exam.title} analytics` : "Exam analytics"}</h2>
          <p className="page-intro">
            Review completion, timing, violations, and question-level patterns for this exam from a
            single admin view.
          </p>
        </div>

        {exam ? (
          <div className="actions">
            <Link to={`/exams/${exam.id}`} className="button-link secondary-button">
              Open Builder
            </Link>
            <Link to={`/exams/${exam.id}/submissions`} className="button-link secondary-button">
              View Submissions
            </Link>
          </div>
        ) : null}
      </div>

      {locationState?.successMessage ? <p className="success-text">{locationState.successMessage}</p> : null}
      {error ? <p className="error">Error: {error}</p> : null}

      {loading ? (
        <section className="panel">
          <p className="state-text">Loading analytics...</p>
        </section>
      ) : null}

      {!loading && analytics ? (
        <>
          <div className="stats-grid analytics-stats-grid">
            <article className="stat-card">
              <span className="stat-label">Total attempts</span>
              <strong>{analytics.exam.total_attempts}</strong>
              <p>All attempts recorded for this exam.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Completed attempts</span>
              <strong>{analytics.exam.completed_attempts}</strong>
              <p>Submitted or force-submitted attempts included in reporting.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Force-submitted</span>
              <strong>{analytics.exam.force_submitted_attempts}</strong>
              <p>Attempts automatically finished when the exam was ended.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Submission rate</span>
              <strong>{formatPercent(analytics.exam.submission_rate_percent)}</strong>
              <p>Completed attempts as a share of total attempts.</p>
            </article>
          </div>

          <div className="analytics-layout">
            <section className="panel">
              <div className="section-heading">
                <div>
                  <h3>Exam summary</h3>
                  <p>High-level completion, duration, and integrity signals for this assessment.</p>
                </div>
              </div>

              <div className="summary-list analytics-summary-list">
                <p>
                  <span>Status</span>
                  <strong>{analytics.exam.is_ended ? "Ended" : "Active"}</strong>
                </p>
                <p>
                  <span>Ended at</span>
                  <strong>{formatTimestamp(analytics.exam.ended_at)}</strong>
                </p>
                <p>
                  <span>Average duration</span>
                  <strong>{formatDuration(analytics.exam.average_exam_duration_seconds)}</strong>
                </p>
                <p>
                  <span>Median duration</span>
                  <strong>{formatDuration(analytics.exam.median_exam_duration_seconds)}</strong>
                </p>
                <p>
                  <span>Min duration</span>
                  <strong>{formatDuration(analytics.exam.min_exam_duration_seconds)}</strong>
                </p>
                <p>
                  <span>Max duration</span>
                  <strong>{formatDuration(analytics.exam.max_exam_duration_seconds)}</strong>
                </p>
                <p>
                  <span>Total violations</span>
                  <strong>{analytics.exam.total_violations}</strong>
                </p>
                <p>
                  <span>Attempts with violations</span>
                  <strong>{formatPercent(analytics.exam.attempts_with_violations_percent)}</strong>
                </p>
                <p>
                  <span>Violations per attempt</span>
                  <strong>{formatNumber(analytics.exam.average_violations_per_attempt)}</strong>
                </p>
                <p>
                  <span>Total screenshots</span>
                  <strong>{analytics.exam.total_screenshots}</strong>
                </p>
                <p>
                  <span>Questions answered per attempt</span>
                  <strong>{formatNumber(analytics.exam.average_questions_answered_per_attempt)}</strong>
                </p>
                <p>
                  <span>Most common violation</span>
                  <strong>{analytics.exam.most_common_violation_type ?? "-"}</strong>
                </p>
              </div>

              {analytics.exam.hardest_question ? (
                <div className="analytics-highlight-card">
                  <span className="stat-label">Hardest question proxy</span>
                  <strong>{analytics.exam.hardest_question.question_text}</strong>
                  <p>
                    {humanizeMetric(analytics.exam.hardest_question.metric)}:{" "}
                    {formatNumber(analytics.exam.hardest_question.value)}
                  </p>
                </div>
              ) : null}
            </section>

            <aside className="panel">
              <div className="section-heading">
                <div>
                  <h3>Metadata and alerts</h3>
                  <p>Timing and alert fields reflect what the current backend can reliably compute.</p>
                </div>
              </div>

              <div className="summary-list analytics-summary-list">
                <p>
                  <span>Question timing</span>
                  <strong>{analytics.metadata.question_time_method}</strong>
                </p>
                <p>
                  <span>Question alerts</span>
                  <strong>{analytics.metadata.question_alert_method}</strong>
                </p>
              </div>

              <div className="analytics-side-section">
                <h4>Highest violation attempts</h4>
                {analytics.exam.attempts_with_highest_violation_count.length === 0 ? (
                  <p className="state-text">No violations recorded for this exam.</p>
                ) : (
                  <div className="analytics-top-list">
                    {analytics.exam.attempts_with_highest_violation_count.map((attempt) => (
                      <div key={attempt.attempt_id} className="analytics-top-item">
                        <div>
                          <strong>{attempt.username ?? "Unknown student"}</strong>
                          <p className="mono analytics-meta-text">{attempt.attempt_id}</p>
                        </div>
                        <span className="alert-badge">{attempt.violation_count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </aside>
          </div>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h3>Question analytics</h3>
                <p>Use this table to spot skipped questions, slow questions, and MCQ answer spread.</p>
              </div>
            </div>

            {analytics.questions.length === 0 ? (
              <p className="state-text">No questions found for this exam.</p>
            ) : (
              <div className="analytics-question-list">
                {analytics.questions.map((question, index) => (
                  <article key={question.question_id} className="analytics-question-card">
                    <div className="builder-question-header">
                      <div>
                        <span className="status-pill">Question {index + 1}</span>
                        <h4>{question.question_text}</h4>
                      </div>
                      {question.correct_rate_percent != null ? (
                        <span className="neutral-badge">
                          Correct rate: {formatPercent(question.correct_rate_percent)}
                        </span>
                      ) : null}
                    </div>

                    <div className="exam-metadata-grid analytics-question-metadata">
                      <p>
                        <span>Total answers</span>
                        <strong>{question.total_answers}</strong>
                      </p>
                      <p>
                        <span>Unanswered</span>
                        <strong>{question.unanswered_count}</strong>
                      </p>
                      <p>
                        <span>Average time</span>
                        <strong>{formatDuration(question.average_time_spent_seconds)}</strong>
                      </p>
                      <p>
                        <span>Average answer length</span>
                        <strong>{formatNumber(question.average_answer_length)}</strong>
                      </p>
                    </div>

                    {question.mcq_option_distribution && question.mcq_option_distribution.length > 0 ? (
                      <div className="table-scroll">
                        <table className="table">
                          <thead>
                            <tr>
                              <th>Option</th>
                              <th>Count</th>
                              <th>Percentage</th>
                            </tr>
                          </thead>
                          <tbody>
                            {question.mcq_option_distribution.map((option) => (
                              <tr key={option.option_id}>
                                <td>{option.option_text}</td>
                                <td>{option.count}</td>
                                <td>{formatPercent(option.percentage)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </section>
  );
}

export default ExamAnalyticsPage;
