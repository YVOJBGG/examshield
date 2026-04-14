import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState, PageHeader, StatCard } from "../components/ui";
import { ApiError, deleteExam, endExam, listExams, type Exam } from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

function formatExamType(examType: Exam["exam_type"]): string {
  return examType === "mcq" ? "MCQ" : "Written";
}

function ExamsListPage({ onAuthError }: Props) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [endingExamId, setEndingExamId] = useState<string | null>(null);

  const summary = useMemo(
    () => ({
      total: exams.length,
      available: exams.filter((exam) => exam.is_available).length,
      mcq: exams.filter((exam) => exam.exam_type === "mcq").length,
      written: exams.filter((exam) => exam.exam_type === "written").length,
    }),
    [exams],
  );

  async function loadExams() {
    setLoading(true);
    setError(null);
    try {
      const data = await listExams();
      setExams(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load exams";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadExams();
  }, []);

  async function onDeleteExam(examId: string) {
    if (!window.confirm("Delete this exam and all related questions?")) {
      return;
    }

    setError(null);
    setSuccessMessage(null);
    try {
      await deleteExam(examId);
      await loadExams();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not delete exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    }
  }

  async function onEndExam(exam: Exam) {
    const confirmed = window.confirm(
      "This will finish all active attempts for this exam. Students still taking it will be submitted automatically.",
    );
    if (!confirmed) {
      return;
    }

    setEndingExamId(exam.id);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await endExam(exam.id);
      setExams((current) =>
        current.map((item) =>
          item.id === exam.id
            ? {
                ...item,
                is_ended: true,
                ended_at: result.ended_at,
                is_available: false,
              }
            : item,
        ),
      );
      const attemptLabel = result.updated_attempts === 1 ? "attempt" : "attempts";
      const success = `Exam ended successfully. ${result.updated_attempts} active ${attemptLabel} were submitted automatically.`;
      setSuccessMessage(success);
      navigate(`/exams/${exam.id}/analytics`, {
        state: { successMessage: success },
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not end exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setEndingExamId(null);
    }
  }

  return (
    <section className="page-section">
      <PageHeader
        eyebrow="Exam Management"
        title="Exam Builder"
        description="Create, organize, and close assessments from one secure administration workspace."
        actions={
          <button type="button" onClick={() => navigate("/exams/new")}>
            Create New Exam
          </button>
        }
      />

      <div className="stats-grid">
        <StatCard
          label="Total exams"
          value={summary.total}
          description="Structured assessments currently configured in the portal."
        />
        <StatCard
          label="Available now"
          value={summary.available}
          description="Exams students can currently enter for a new attempt."
        />
        <StatCard
          label="MCQ exams"
          value={summary.mcq}
          description="Auto-graded assessments with answer options and correct choices."
        />
        <StatCard
          label="Written exams"
          value={summary.written}
          description="Open-response assessments designed for manual grading workflows."
        />
      </div>

      {error && <p className="error">Error: {error}</p>}
      {successMessage && <p className="success-text">{successMessage}</p>}

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>Assessment library</h3>
            <p>Each exam shows its type, public ID, student availability, and core settings.</p>
          </div>
        </div>

        {loading && <p className="state-text">Loading exams...</p>}

        {!loading && (
          <div className="exam-grid">
            {exams.map((exam) => (
              <article key={exam.id} className="exam-overview-card">
                <div className="exam-overview-header">
                  <div className="exam-overview-title">
                    <span className={`type-badge ${exam.exam_type}`}>{formatExamType(exam.exam_type)}</span>
                    <h3>{exam.title}</h3>
                  </div>
                  <span
                    className={
                      exam.is_ended
                        ? "availability-pill ended"
                        : exam.is_available
                          ? "availability-pill available"
                          : "availability-pill unavailable"
                    }
                  >
                    {exam.is_ended ? "Ended" : exam.is_available ? "Available" : "Unavailable"}
                  </span>
                </div>

                <div className="exam-metadata-grid">
                  <p>
                    <span>Exam ID</span>
                    <strong className="mono">{exam.exam_code}</strong>
                  </p>
                  <p>
                    <span>Time limit</span>
                    <strong>{exam.time_limit_minutes} min</strong>
                  </p>
                  <p>
                    <span>Builder mode</span>
                    <strong>{formatExamType(exam.exam_type)}</strong>
                  </p>
                  <p>
                    <span>Instructions</span>
                    <strong>{exam.instructions?.trim() ? "Included" : "Not set"}</strong>
                  </p>
                  <p>
                    <span>Exam status</span>
                    <strong>{exam.is_ended ? "Ended" : "Active"}</strong>
                  </p>
                </div>

                <div className="exam-card-actions">
                  <button type="button" className="secondary-button" onClick={() => navigate(`/exams/${exam.id}`)}>
                    Open Builder
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => navigate(`/exams/${exam.id}/submissions`)}
                  >
                    View Submissions
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => navigate(`/exams/${exam.id}/analytics`)}
                  >
                    View Analytics
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => void onEndExam(exam)}
                    disabled={endingExamId === exam.id || exam.is_ended}
                  >
                    {exam.is_ended ? "Exam Ended" : endingExamId === exam.id ? "Ending..." : "End Exam"}
                  </button>
                  <button type="button" className="danger" onClick={() => void onDeleteExam(exam.id)}>
                    Delete
                  </button>
                </div>
              </article>
            ))}

            {exams.length === 0 && (
              <EmptyState
                title="No exams yet"
                description="Start with a written or MCQ assessment and build the full structure from one editor."
                action={
                  <button type="button" onClick={() => navigate("/exams/new")}>
                    Create your first exam
                  </button>
                }
              />
            )}
          </div>
        )}
      </section>
    </section>
  );
}

export default ExamsListPage;
