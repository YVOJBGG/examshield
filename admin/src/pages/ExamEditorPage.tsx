import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  createQuestion,
  deleteExam,
  deleteQuestion,
  getExam,
  listQuestions,
  updateExam,
  updateQuestion,
  type Exam,
  type Question,
} from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

function ExamEditorPage({ onAuthError }: Props) {
  const navigate = useNavigate();
  const { examId } = useParams<{ examId: string }>();

  const resolvedExamId = useMemo(() => examId ?? "", [examId]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [savingExam, setSavingExam] = useState(false);
  const [newQuestionText, setNewQuestionText] = useState("");
  const [questionDrafts, setQuestionDrafts] = useState<Record<string, string>>({});

  async function loadData() {
    if (!resolvedExamId) {
      setError("Missing exam id.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [examData, questionData] = await Promise.all([getExam(resolvedExamId), listQuestions(resolvedExamId)]);
      setExam(examData);
      setQuestions(questionData);
      setQuestionDrafts(
        questionData.reduce<Record<string, string>>((acc, item) => {
          acc[item.id] = item.text;
          return acc;
        }, {}),
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [resolvedExamId]);

  async function onSaveExam(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!exam) {
      return;
    }
    setSavingExam(true);
    setError(null);
    try {
      const updated = await updateExam(exam.id, {
        title: exam.title,
        time_limit_minutes: exam.time_limit_minutes,
      });
      setExam(updated);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not update exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setSavingExam(false);
    }
  }

  async function onDeleteExam() {
    if (!exam || !window.confirm("Delete this exam and all questions?")) {
      return;
    }

    setError(null);
    try {
      await deleteExam(exam.id);
      navigate("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not delete exam";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    }
  }

  async function onAddQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!exam) {
      return;
    }
    setError(null);
    try {
      await createQuestion(exam.id, { text: newQuestionText });
      setNewQuestionText("");
      await loadData();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not add question";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    }
  }

  async function onSaveQuestion(questionId: string) {
    if (!exam) {
      return;
    }
    setError(null);
    try {
      const updated = await updateQuestion(exam.id, questionId, { text: questionDrafts[questionId] });
      setQuestions((prev) => prev.map((q) => (q.id === questionId ? updated : q)));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not update question";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    }
  }

  async function onDeleteQuestion(questionId: string) {
    if (!exam || !window.confirm("Delete this question?")) {
      return;
    }
    setError(null);
    try {
      await deleteQuestion(exam.id, questionId);
      setQuestions((prev) => prev.filter((q) => q.id !== questionId));
      setQuestionDrafts((prev) => {
        const next = { ...prev };
        delete next[questionId];
        return next;
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not delete question";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    }
  }

  if (loading) {
    return (
      <section className="panel">
        <p>Loading exam...</p>
      </section>
    );
  }

  if (!exam) {
    return (
      <section className="panel">
        <p className="error">Exam not found.</p>
        <Link to="/">Back to exams</Link>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="toolbar">
        <Link to="/">Back to exams</Link>
        <button type="button" className="danger" onClick={() => void onDeleteExam()}>
          Delete Exam
        </button>
      </div>

      <h2>Exam Editor</h2>
      {error && <p className="error">Error: {error}</p>}

      <form className="inline-form" onSubmit={onSaveExam}>
        <input
          value={exam.title}
          onChange={(event) => setExam({ ...exam, title: event.target.value })}
          placeholder="Exam title"
          required
        />
        <input
          type="number"
          min={1}
          value={exam.time_limit_minutes}
          onChange={(event) => setExam({ ...exam, time_limit_minutes: Number(event.target.value) })}
          required
        />
        <button type="submit" disabled={savingExam}>
          {savingExam ? "Saving..." : "Save Exam"}
        </button>
      </form>

      <h3>Questions</h3>
      <form className="inline-form" onSubmit={onAddQuestion}>
        <input
          value={newQuestionText}
          onChange={(event) => setNewQuestionText(event.target.value)}
          placeholder="New question text"
          required
        />
        <button type="submit">Add Question</button>
      </form>

      <div className="questions">
        {questions.map((question) => (
          <div key={question.id} className="question-item">
            <textarea
              value={questionDrafts[question.id] ?? ""}
              onChange={(event) =>
                setQuestionDrafts((prev) => ({ ...prev, [question.id]: event.target.value }))
              }
            />
            <div className="actions">
              <button type="button" onClick={() => void onSaveQuestion(question.id)}>
                Save
              </button>
              <button type="button" className="danger" onClick={() => void onDeleteQuestion(question.id)}>
                Delete
              </button>
            </div>
          </div>
        ))}
        {questions.length === 0 && <p>No questions yet.</p>}
      </div>
    </section>
  );
}

export default ExamEditorPage;
