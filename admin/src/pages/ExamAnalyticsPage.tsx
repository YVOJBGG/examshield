import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { ApiError, getExam, getExamAnalytics, type Exam, type ExamAnalyticsQuestion, type ExamAnalyticsResponse } from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

type LocationState = {
  successMessage?: string;
};

type InsightItem = {
  label: string;
  value: string;
  note: string;
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
      return "Highest average time spent";
    default:
      return metric ?? "-";
  }
}

function buildInsights(analytics: ExamAnalyticsResponse): InsightItem[] {
  const items: InsightItem[] = [];
  const highestTimeQuestion = analytics.questions.reduce<ExamAnalyticsQuestion | null>((current, question) => {
    if (question.average_time_spent_seconds == null) {
      return current;
    }
    if (current == null) {
      return question;
    }
    return (question.average_time_spent_seconds ?? 0) > (current.average_time_spent_seconds ?? 0) ? question : current;
  }, null);

  if (highestTimeQuestion) {
    items.push({
      label: "Longest question",
      value: highestTimeQuestion.question_text,
      note: `Avg. time per question (estimated): ${formatDuration(highestTimeQuestion.average_time_spent_seconds)}`,
    });
  }

  const mostUnansweredQuestion = analytics.questions.reduce<ExamAnalyticsQuestion | null>((current, question) => {
    if (current == null) {
      return question;
    }
    return question.unanswered_count > current.unanswered_count ? question : current;
  }, null);

  if (mostUnansweredQuestion && mostUnansweredQuestion.unanswered_count > 0) {
    items.push({
      label: "Most skipped question",
      value: mostUnansweredQuestion.question_text,
      note: `${mostUnansweredQuestion.unanswered_count} unanswered submissions`,
    });
  }

  if (analytics.exam.most_common_violation_type) {
    items.push({
      label: "Most common violation",
      value: analytics.exam.most_common_violation_type,
      note: `${analytics.exam.total_violations} total recorded violations`,
    });
  }

  const topFlaggedAttempt = analytics.exam.attempts_with_highest_violation_count[0];
  if (topFlaggedAttempt) {
    items.push({
      label: "Top flagged attempt",
      value: topFlaggedAttempt.username ?? "Unknown student",
      note: `${topFlaggedAttempt.violation_count} violation${topFlaggedAttempt.violation_count === 1 ? "" : "s"}`,
    });
  }

  if (analytics.exam.hardest_question) {
    items.push({
      label: "Backend hardest-question proxy",
      value: analytics.exam.hardest_question.question_text,
      note: `${humanizeMetric(analytics.exam.hardest_question.metric)}: ${formatNumber(analytics.exam.hardest_question.value)}`,
    });
  }

  return items;
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

  const insights = useMemo(() => (analytics ? buildInsights(analytics) : []), [analytics]);
  const hasAttempts = (analytics?.exam.total_attempts ?? 0) > 0;

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
            Review completion outcomes, question behavior, and monitoring patterns for this exam in
            a clean, export-friendly layout.
          </p>
        </div>

        {exam ? (
          <div className="actions">
            <Link to={`/exams/${exam.id}`} className="button-link">
              Open Builder
            </Link>
            <Link to={`/exams/${exam.id}/submissions`} className="button-link">
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
              <span className="stat-label">Exam title</span>
              <strong>{analytics.exam.exam_title}</strong>
              <p>{analytics.exam.is_ended ? "Exam ended and ready for analysis." : "Exam analytics snapshot."}</p>
            </article>
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
            <article className="stat-card">
              <span className="stat-label">Average duration</span>
              <strong>{formatDuration(analytics.exam.average_exam_duration_seconds)}</strong>
              <p>Average time from attempt start to submission.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Total violations</span>
              <strong>{analytics.exam.total_violations}</strong>
              <p>All monitoring violations recorded for this exam.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Violations per attempt</span>
              <strong>{formatNumber(analytics.exam.average_violations_per_attempt)}</strong>
              <p>Average violations across all attempts.</p>
            </article>
            <article className="stat-card">
              <span className="stat-label">Attempts with violations</span>
              <strong>{formatPercent(analytics.exam.attempts_with_violations_percent)}</strong>
              <p>Share of attempts that had at least one violation.</p>
            </article>
          </div>

          {!hasAttempts ? (
            <section className="panel empty-state-card analytics-empty-state">
              <h3>No analytics yet</h3>
              <p>
                This exam does not have any attempts yet, so there are no outcomes or monitoring
                patterns to summarize.
              </p>
            </section>
          ) : (
            <>
              <div className="analytics-layout">
                <section className="panel">
                  <div className="section-heading">
                    <div>
                      <h3>Top summary</h3>
                      <p>Core exam-level outcomes and monitoring signals for this assessment.</p>
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
                      <span>Minimum duration</span>
                      <strong>{formatDuration(analytics.exam.min_exam_duration_seconds)}</strong>
                    </p>
                    <p>
                      <span>Maximum duration</span>
                      <strong>{formatDuration(analytics.exam.max_exam_duration_seconds)}</strong>
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
                    <p>
                      <span>Question timing method</span>
                      <strong>{analytics.metadata.question_time_method}</strong>
                    </p>
                    <p>
                      <span>Question alerts method</span>
                      <strong>{analytics.metadata.question_alert_method}</strong>
                    </p>
                  </div>
                </section>

                <aside className="panel">
                  <div className="section-heading">
                    <div>
                      <h3>Additional insights</h3>
                      <p>Highlights interpreted client-side from the returned analytics payload.</p>
                    </div>
                  </div>

                  {insights.length === 0 ? (
                    <p className="state-text">No additional insights are available for this exam yet.</p>
                  ) : (
                    <div className="analytics-insight-list">
                      {insights.map((item) => (
                        <article key={`${item.label}-${item.value}`} className="analytics-highlight-card">
                          <span className="stat-label">{item.label}</span>
                          <strong>{item.value}</strong>
                          <p>{item.note}</p>
                        </article>
                      ))}
                    </div>
                  )}
                </aside>
              </div>

              <section className="panel">
                <div className="section-heading">
                  <div>
                    <h3>Question analytics</h3>
                    <p>
                      Use this section to spot skipped questions, slower questions, and answer
                      patterns. Avg. time per question is estimated when that is how the backend
                      provides it.
                    </p>
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
                            <span>Avg. time (estimated)</span>
                            <strong>{formatDuration(question.average_time_spent_seconds)}</strong>
                          </p>
                          <p>
                            <span>Total answers</span>
                            <strong>{question.total_answers}</strong>
                          </p>
                          <p>
                            <span>Unanswered count</span>
                            <strong>{question.unanswered_count}</strong>
                          </p>
                          <p>
                            <span>Alert count</span>
                            <strong>{question.alert_count_for_question == null ? "Not available" : question.alert_count_for_question}</strong>
                          </p>
                          <p>
                            <span>Average answer length</span>
                            <strong>{formatNumber(question.average_answer_length)}</strong>
                          </p>
                        </div>

                        {question.mcq_option_distribution && question.mcq_option_distribution.length > 0 ? (
                          <div className="analytics-mcq-section">
                            <div className="section-heading compact">
                              <div>
                                <h5>Option distribution</h5>
                                <p>Percentages are based on answers recorded for this question.</p>
                              </div>
                            </div>

                            <div className="analytics-option-list">
                              {question.mcq_option_distribution.map((option) => (
                                <div key={option.option_id} className="analytics-option-row">
                                  <div className="analytics-option-head">
                                    <strong>{option.option_text}</strong>
                                    <span>
                                      {formatPercent(option.percentage)} ({option.count})
                                    </span>
                                  </div>
                                  <div className="analytics-option-bar-track" aria-hidden="true">
                                    <div
                                      className="analytics-option-bar-fill"
                                      style={{ width: `${Math.max(0, Math.min(option.percentage, 100))}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </article>
                    ))}
                  </div>
                )}
              </section>

              {analytics.exam.attempts_with_highest_violation_count.length > 0 ? (
                <section className="panel">
                  <div className="section-heading">
                    <div>
                      <h3>Attempts and violations spotlight</h3>
                      <p>Attempts with the highest recorded violation counts for this exam.</p>
                    </div>
                  </div>

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
                </section>
              ) : null}
            </>
          )}
        </>
      ) : null}
    </section>
  );
}

export default ExamAnalyticsPage;
