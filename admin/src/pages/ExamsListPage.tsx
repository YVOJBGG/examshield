import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, createExam, deleteExam, listExams, type Exam } from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

function ExamsListPage({ onAuthError }: Props) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [title, setTitle] = useState("");
  const [timeLimit, setTimeLimit] = useState(60);
  const [submitting, setSubmitting] = useState(false);

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

  async function onCreateExam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await createExam({ title, time_limit_minutes: timeLimit });
      setTitle("");
      setTimeLimit(60);
      await loadExams();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not create exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onDeleteExam(examId: string) {
    if (!window.confirm("Delete this exam and all related questions?")) {
      return;
    }
    setError(null);
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

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <span className="eyebrow">Exam Management</span>
          <h2>Assessments</h2>
          <p className="page-intro">
            Create new exams, share their teacher-facing Exam IDs, and jump into editing or review
            workflows.
          </p>
        </div>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Total exams</span>
          <strong>{exams.length}</strong>
          <p>All configured assessments available to students.</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Available now</span>
          <strong>{exams.filter((exam) => exam.is_available).length}</strong>
          <p>Exams students can currently start for the first time.</p>
        </article>
        <article className="stat-card">
          <span className="stat-label">Default timer</span>
          <strong>{timeLimit} min</strong>
          <p>New exams start with this duration unless you adjust it before saving.</p>
        </article>
      </div>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>Create exam</h3>
            <p>Set a title and time limit. The server will generate a shareable Exam ID.</p>
          </div>
        </div>

        <form className="inline-form" onSubmit={onCreateExam}>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Exam title"
            required
          />
          <input
            type="number"
            min={1}
            value={timeLimit}
            onChange={(event) => setTimeLimit(Number(event.target.value))}
            required
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create New Exam"}
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div>
            <h3>Existing exams</h3>
            <p>Open an exam to edit questions or review submissions.</p>
          </div>
        </div>

        {loading && <p className="state-text">Loading exams...</p>}
        {error && <p className="error">Error: {error}</p>}

        {!loading && (
          <div className="table-scroll">
            <table className="table">
              <thead>
                <tr>
                  <th>Exam ID</th>
                  <th>Title</th>
                  <th>Availability</th>
                  <th>Time Limit</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.id}>
                    <td>
                      <span className="mono id-chip">{exam.exam_code}</span>
                    </td>
                    <td>
                      <strong>{exam.title}</strong>
                    </td>
                    <td>
                      <span className={exam.is_available ? "availability-pill available" : "availability-pill unavailable"}>
                        {exam.is_available ? "Available" : "Unavailable"}
                      </span>
                    </td>
                    <td>{exam.time_limit_minutes} min</td>
                    <td className="actions">
                      <button type="button" className="secondary-button" onClick={() => navigate(`/exams/${exam.id}`)}>
                        Open
                      </button>
                      <button type="button" className="danger" onClick={() => void onDeleteExam(exam.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
                {exams.length === 0 && (
                  <tr>
                    <td colSpan={5} className="empty-cell">No exams yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </section>
  );
}

export default ExamsListPage;
