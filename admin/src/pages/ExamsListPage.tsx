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
    <section className="panel">
      <h2>Exams</h2>

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

      {loading && <p>Loading exams...</p>}
      {error && <p className="error">Error: {error}</p>}

      {!loading && (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Time Limit</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {exams.map((exam) => (
              <tr key={exam.id}>
                <td>{exam.title}</td>
                <td>{exam.time_limit_minutes} min</td>
                <td className="actions">
                  <button type="button" onClick={() => navigate(`/exams/${exam.id}`)}>
                    Edit
                  </button>
                  <button type="button" className="danger" onClick={() => void onDeleteExam(exam.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {exams.length === 0 && (
              <tr>
                <td colSpan={3}>No exams yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default ExamsListPage;
