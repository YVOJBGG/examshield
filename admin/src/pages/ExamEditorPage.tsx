import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  createExam,
  createQuestion,
  deleteExam,
  deleteQuestion,
  getExamDetail,
  updateExam,
  updateQuestion,
  type Exam,
  type ExamCreate,
  type ExamDetail,
  type Question,
  type QuestionCreate,
  type QuestionOptionCreate,
} from "../lib/api";

type Props = {
  onAuthError: (message: string) => void;
};

type DraftOption = {
  localId: string;
  id?: string;
  option_text: string;
  is_correct: boolean;
};

type DraftQuestion = {
  localId: string;
  id?: string;
  text: string;
  points: number;
  options: DraftOption[];
};

type BuilderDraft = {
  title: string;
  exam_type: "mcq" | "written";
  time_limit_minutes: number;
  is_available: boolean;
  instructions: string;
  questions: DraftQuestion[];
};

type ValidationSummary = {
  examIssues: string[];
  questionIssues: Record<string, string[]>;
};

const DEFAULT_EXAM: BuilderDraft = {
  title: "",
  exam_type: "written",
  time_limit_minutes: 60,
  is_available: true,
  instructions: "",
  questions: [],
};

function newLocalId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

function createEmptyOption(): DraftOption {
  return {
    localId: newLocalId("option"),
    option_text: "",
    is_correct: false,
  };
}

function createEmptyQuestion(examType: BuilderDraft["exam_type"]): DraftQuestion {
  return {
    localId: newLocalId("question"),
    text: "",
    points: 1,
    options: examType === "mcq" ? [createEmptyOption(), createEmptyOption()] : [],
  };
}

function mapExamDetailToDraft(exam: ExamDetail): BuilderDraft {
  return {
    title: exam.title,
    exam_type: exam.exam_type,
    time_limit_minutes: exam.time_limit_minutes,
    is_available: exam.is_available,
    instructions: exam.instructions ?? "",
    questions: exam.questions
      .slice()
      .sort((left, right) => left.order_index - right.order_index)
      .map((question) => ({
        localId: newLocalId("question"),
        id: question.id,
        text: question.text,
        points: question.points,
        options: question.options
          .slice()
          .sort((left, right) => left.order_index - right.order_index)
          .map((option) => ({
            localId: newLocalId("option"),
            id: option.id,
            option_text: option.option_text,
            is_correct: option.is_correct,
          })),
      })),
  };
}

function toExamPayload(draft: BuilderDraft): ExamCreate {
  return {
    title: draft.title.trim(),
    exam_type: draft.exam_type,
    time_limit_minutes: draft.time_limit_minutes,
    is_available: draft.is_available,
    instructions: draft.instructions.trim() || null,
  };
}

function toQuestionPayload(question: DraftQuestion, orderIndex: number, examType: BuilderDraft["exam_type"]): QuestionCreate {
  const payload: QuestionCreate = {
    text: question.text.trim(),
    points: question.points,
    order_index: orderIndex,
  };

  if (examType === "mcq") {
    payload.options = question.options.map<QuestionOptionCreate>((option, optionIndex) => ({
      option_text: option.option_text.trim(),
      is_correct: option.is_correct,
      order_index: optionIndex,
    }));
  }

  return payload;
}

function duplicateQuestion(question: DraftQuestion): DraftQuestion {
  return {
    ...question,
    id: undefined,
    localId: newLocalId("question"),
    options: question.options.map((option) => ({
      ...option,
      id: undefined,
      localId: newLocalId("option"),
    })),
  };
}

function formatExamType(examType: BuilderDraft["exam_type"]): string {
  return examType === "mcq" ? "MCQ exam" : "Written exam";
}

function buildValidationSummary(draft: BuilderDraft): ValidationSummary {
  const examIssues: string[] = [];
  const questionIssues: Record<string, string[]> = {};

  if (!draft.title.trim()) {
    examIssues.push("Title is required.");
  }
  if (draft.time_limit_minutes <= 0 || Number.isNaN(draft.time_limit_minutes)) {
    examIssues.push("Time limit must be greater than 0.");
  }
  if (draft.questions.length === 0) {
    examIssues.push("Add at least one question before saving.");
  }

  draft.questions.forEach((question, index) => {
    const issues: string[] = [];
    if (!question.text.trim()) {
      issues.push(`Question ${index + 1} needs prompt text.`);
    }
    if (question.points <= 0 || Number.isNaN(question.points)) {
      issues.push(`Question ${index + 1} must have points greater than 0.`);
    }

    if (draft.exam_type === "mcq") {
      if (question.options.length < 2) {
        issues.push("MCQ questions need at least 2 options.");
      }
      if (question.options.some((option) => !option.option_text.trim())) {
        issues.push("Each option needs text.");
      }
      if (question.options.filter((option) => option.is_correct).length !== 1) {
        issues.push("Select exactly 1 correct option for v1.");
      }
    }

    if (issues.length > 0) {
      questionIssues[question.localId] = issues;
    }
  });

  return { examIssues, questionIssues };
}

function totalPoints(questions: DraftQuestion[]): number {
  return questions.reduce((sum, question) => sum + (Number.isFinite(question.points) ? question.points : 0), 0);
}

function ExamEditorPage({ onAuthError }: Props) {
  const navigate = useNavigate();
  const { examId } = useParams<{ examId: string }>();

  const isCreateMode = !examId || examId === "new";
  const [loading, setLoading] = useState(!isCreateMode);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const [draft, setDraft] = useState<BuilderDraft>(DEFAULT_EXAM);
  const [saving, setSaving] = useState(false);

  const validation = useMemo(() => buildValidationSummary(draft), [draft]);
  const totalValidationIssues =
    validation.examIssues.length +
    Object.values(validation.questionIssues).reduce((sum, items) => sum + items.length, 0);

  async function loadExam() {
    if (isCreateMode || !examId) {
      setLoading(false);
      setExam(null);
      setDraft(DEFAULT_EXAM);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const examData = await getExamDetail(examId);
      setExam(examData);
      setDraft(mapExamDetailToDraft(examData));
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
    void loadExam();
  }, [examId]);

  function updateDraft(patch: Partial<BuilderDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateQuestionDraft(localId: string, patch: Partial<DraftQuestion>) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question) =>
        question.localId === localId ? { ...question, ...patch } : question,
      ),
    }));
  }

  function setExamType(examType: BuilderDraft["exam_type"]) {
    setDraft((current) => ({
      ...current,
      exam_type: examType,
      questions: current.questions.map((question) => ({
        ...question,
        options:
          examType === "mcq"
            ? question.options.length >= 2
              ? question.options
              : [createEmptyOption(), createEmptyOption()]
            : [],
      })),
    }));
  }

  function addQuestion() {
    setDraft((current) => ({
      ...current,
      questions: [...current.questions, createEmptyQuestion(current.exam_type)],
    }));
  }

  function removeQuestion(localId: string) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.filter((question) => question.localId !== localId),
    }));
  }

  function cloneQuestion(localId: string) {
    setDraft((current) => {
      const nextQuestions: DraftQuestion[] = [];
      current.questions.forEach((question) => {
        nextQuestions.push(question);
        if (question.localId === localId) {
          nextQuestions.push(duplicateQuestion(question));
        }
      });
      return { ...current, questions: nextQuestions };
    });
  }

  function addOption(questionLocalId: string) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question) =>
        question.localId === questionLocalId
          ? { ...question, options: [...question.options, createEmptyOption()] }
          : question,
      ),
    }));
  }

  function updateOption(questionLocalId: string, optionLocalId: string, patch: Partial<DraftOption>) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question) => {
        if (question.localId !== questionLocalId) {
          return question;
        }

        return {
          ...question,
          options: question.options.map((option) =>
            option.localId === optionLocalId ? { ...option, ...patch } : option,
          ),
        };
      }),
    }));
  }

  function markCorrectOption(questionLocalId: string, optionLocalId: string) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question) => {
        if (question.localId !== questionLocalId) {
          return question;
        }

        return {
          ...question,
          options: question.options.map((option) => ({
            ...option,
            is_correct: option.localId === optionLocalId,
          })),
        };
      }),
    }));
  }

  function removeOption(questionLocalId: string, optionLocalId: string) {
    setDraft((current) => ({
      ...current,
      questions: current.questions.map((question) => {
        if (question.localId !== questionLocalId) {
          return question;
        }

        const nextOptions = question.options.filter((option) => option.localId !== optionLocalId);
        return {
          ...question,
          options: nextOptions,
        };
      }),
    }));
  }

  async function syncQuestions(examEntity: Exam, existingQuestions: Question[]) {
    const existingById = new Map(existingQuestions.map((question) => [question.id, question]));
    const draftIds = new Set(draft.questions.flatMap((question) => (question.id ? [question.id] : [])));

    for (const existingQuestion of existingQuestions) {
      if (!draftIds.has(existingQuestion.id)) {
        await deleteQuestion(examEntity.id, existingQuestion.id);
      }
    }

    for (const [index, question] of draft.questions.entries()) {
      const payload = toQuestionPayload(question, index, draft.exam_type);
      if (question.id && existingById.has(question.id)) {
        await updateQuestion(examEntity.id, question.id, payload);
      } else {
        await createQuestion(examEntity.id, payload);
      }
    }
  }

  async function onSaveBuilder() {
    const nextValidation = buildValidationSummary(draft);
    if (
      nextValidation.examIssues.length > 0 ||
      Object.keys(nextValidation.questionIssues).length > 0
    ) {
      setError("Resolve the highlighted validation issues before saving.");
      setSuccess(null);
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    try {
      let savedExam: Exam;

      if (isCreateMode) {
        savedExam = await createExam(toExamPayload(draft));
      } else {
        if (!examId) {
          throw new Error("Missing exam id.");
        }
        savedExam = await updateExam(examId, toExamPayload(draft));
      }

      const examDetail = isCreateMode ? ({ ...savedExam, questions: [] } as ExamDetail) : await getExamDetail(savedExam.id);
      await syncQuestions(savedExam, examDetail.questions);

      setSuccess(isCreateMode ? "Exam created successfully." : "Exam updated successfully.");

      if (isCreateMode) {
        navigate(`/exams/${savedExam.id}`, { replace: true });
        return;
      }

      await loadExam();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not save exam builder";
      setError(message);
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        onAuthError("Authentication failed or insufficient permissions. Please login as admin.");
      }
    } finally {
      setSaving(false);
    }
  }

  async function onDeleteCurrentExam() {
    if (isCreateMode || !exam || !window.confirm("Delete this exam and all questions?")) {
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

  if (loading) {
    return (
      <section className="panel">
        <p className="state-text">Loading exam builder...</p>
      </section>
    );
  }

  return (
    <section className="page-section">
      <div className="page-header">
        <div className="page-heading-block">
          <Link to="/" className="back-link">
            Back to exams
          </Link>
          <span className="eyebrow">{isCreateMode ? "New Assessment" : "Edit Assessment"}</span>
          <h2>{isCreateMode ? "Exam Builder" : draft.title || "Untitled exam"}</h2>
          <p className="page-intro">
            Author the full assessment structure in one place, including exam settings, ordered
            questions, points, and MCQ answer keys where needed.
          </p>
        </div>

        <div className="actions">
          {!isCreateMode && exam ? (
            <button type="button" className="secondary-button" onClick={() => navigate(`/exams/${exam.id}/submissions`)}>
              View Submissions
            </button>
          ) : null}
          {!isCreateMode ? (
            <button type="button" className="danger" onClick={() => void onDeleteCurrentExam()}>
              Delete Exam
            </button>
          ) : null}
          <button type="button" onClick={() => void onSaveBuilder()} disabled={saving}>
            {saving ? "Saving..." : isCreateMode ? "Create Exam" : "Save Builder"}
          </button>
        </div>
      </div>

      {error && <p className="error">Error: {error}</p>}
      {success && <p className="success-text">{success}</p>}

      <div className="builder-layout">
        <div className="builder-main">
          <section className="panel">
            <div className="section-heading">
              <div>
                <h3>Exam identity and configuration</h3>
                <p>Set the exam type, timing, availability, and author guidance before saving.</p>
              </div>
            </div>

            <div className="builder-section-grid">
              <label className="field-stack">
                <span>Title</span>
                <input
                  value={draft.title}
                  onChange={(event) => updateDraft({ title: event.target.value })}
                  placeholder="Distributed Systems Midterm"
                />
              </label>

              <div className="field-stack">
                <span>Exam type</span>
                <div className="type-selector">
                  <button
                    type="button"
                    className={draft.exam_type === "written" ? "type-tile active" : "type-tile"}
                    onClick={() => setExamType("written")}
                  >
                    <strong>Written exam</strong>
                    <span>Open-response questions graded manually.</span>
                  </button>
                  <button
                    type="button"
                    className={draft.exam_type === "mcq" ? "type-tile active" : "type-tile"}
                    onClick={() => setExamType("mcq")}
                  >
                    <strong>MCQ exam</strong>
                    <span>Single-correct multiple choice with auto-grading.</span>
                  </button>
                </div>
              </div>

              <label className="field-stack">
                <span>Time limit (minutes)</span>
                <input
                  type="number"
                  min={1}
                  value={draft.time_limit_minutes}
                  onChange={(event) =>
                    updateDraft({ time_limit_minutes: Number(event.target.value) })
                  }
                />
              </label>

              <label className="field-stack">
                <span>Exam ID</span>
                <div className="readonly-field mono">{exam?.exam_code ?? "Generated after first save"}</div>
              </label>

              <label className="field-stack field-span-full">
                <span>Instructions</span>
                <textarea
                  value={draft.instructions}
                  onChange={(event) => updateDraft({ instructions: event.target.value })}
                  placeholder="Provide exam instructions, allowed materials, or response expectations."
                />
              </label>

              <label className="toggle-field field-span-full">
                <input
                  type="checkbox"
                  checked={draft.is_available}
                  onChange={(event) => updateDraft({ is_available: event.target.checked })}
                />
                <span>Make this exam available for students to start</span>
              </label>
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h3>{draft.exam_type === "mcq" ? "MCQ question builder" : "Written question builder"}</h3>
                <p>
                  {draft.exam_type === "mcq"
                    ? "Create clear prompts, define answer options, and mark the correct choice."
                    : "Create open-ended prompts with stable ordering and point values."}
                </p>
              </div>
              <button type="button" className="secondary-button" onClick={addQuestion}>
                Add Question
              </button>
            </div>

            <div className="builder-question-list">
              {draft.questions.map((question, index) => {
                const issues = validation.questionIssues[question.localId] ?? [];

                return (
                  <article key={question.localId} className="builder-question-card">
                    <div className="builder-question-header">
                      <div>
                        <span className="status-pill">Question {index + 1}</span>
                        <h4>{draft.exam_type === "mcq" ? "Multiple-choice prompt" : "Written prompt"}</h4>
                      </div>
                      <div className="actions">
                        <button type="button" className="secondary-button" onClick={() => cloneQuestion(question.localId)}>
                          Duplicate
                        </button>
                        <button type="button" className="danger" onClick={() => removeQuestion(question.localId)}>
                          Remove
                        </button>
                      </div>
                    </div>

                    <div className="builder-question-grid">
                      <label className="field-stack field-span-full">
                        <span>Question prompt</span>
                        <textarea
                          value={question.text}
                          onChange={(event) => updateQuestionDraft(question.localId, { text: event.target.value })}
                          placeholder={
                            draft.exam_type === "mcq"
                              ? "Write the stem students will answer."
                              : "Write the written response prompt."
                          }
                        />
                      </label>

                      <label className="field-stack">
                        <span>Points</span>
                        <input
                          type="number"
                          min={1}
                          value={question.points}
                          onChange={(event) =>
                            updateQuestionDraft(question.localId, { points: Number(event.target.value) })
                          }
                        />
                      </label>

                      <label className="field-stack">
                        <span>Order</span>
                        <div className="readonly-field">#{index + 1}</div>
                      </label>
                    </div>

                    {draft.exam_type === "mcq" ? (
                      <div className="mcq-options-section">
                        <div className="section-heading compact">
                          <div>
                            <h5>Options</h5>
                            <p>Select exactly one correct option for this version.</p>
                          </div>
                          <button type="button" className="secondary-button" onClick={() => addOption(question.localId)}>
                            Add Option
                          </button>
                        </div>

                        <div className="option-list">
                          {question.options.map((option, optionIndex) => (
                            <div key={option.localId} className="option-row">
                              <label className="option-correct-toggle">
                                <input
                                  type="radio"
                                  name={`correct-${question.localId}`}
                                  checked={option.is_correct}
                                  onChange={() => markCorrectOption(question.localId, option.localId)}
                                />
                                <span>Correct</span>
                              </label>

                              <div className="field-stack option-input">
                                <span>Option {optionIndex + 1}</span>
                                <input
                                  value={option.option_text}
                                  onChange={(event) =>
                                    updateOption(question.localId, option.localId, {
                                      option_text: event.target.value,
                                    })
                                  }
                                  placeholder={`Option ${optionIndex + 1} text`}
                                />
                              </div>

                              <button
                                type="button"
                                className="secondary-button option-delete"
                                onClick={() => removeOption(question.localId, option.localId)}
                              >
                                Remove
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {issues.length > 0 ? (
                      <div className="validation-list">
                        {issues.map((issue) => (
                          <p key={issue} className="validation-hint">
                            {issue}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </article>
                );
              })}

              {draft.questions.length === 0 ? (
                <div className="empty-state-card">
                  <h3>No questions yet</h3>
                  <p>
                    Add your first {draft.exam_type === "mcq" ? "multiple-choice" : "written"} question to start
                    building the assessment.
                  </p>
                  <button type="button" onClick={addQuestion}>
                    Add First Question
                  </button>
                </div>
              ) : null}
            </div>
          </section>
        </div>

        <aside className="builder-sidebar">
          <section className="panel">
            <div className="section-heading">
              <div>
                <h3>Builder summary</h3>
                <p>Quick status before you publish or keep iterating.</p>
              </div>
            </div>

            <div className="summary-list">
              <p>
                <span>Mode</span>
                <strong>{formatExamType(draft.exam_type)}</strong>
              </p>
              <p>
                <span>Questions</span>
                <strong>{draft.questions.length}</strong>
              </p>
              <p>
                <span>Total points</span>
                <strong>{totalPoints(draft.questions)}</strong>
              </p>
              <p>
                <span>Availability</span>
                <strong>{draft.is_available ? "Available" : "Unavailable"}</strong>
              </p>
              <p>
                <span>Exam ID</span>
                <strong className="mono">{exam?.exam_code ?? "Pending"}</strong>
              </p>
            </div>
          </section>

          <section className="panel">
            <div className="section-heading">
              <div>
                <h3>Validation</h3>
                <p>Use these checks to avoid broken exam structures before saving.</p>
              </div>
            </div>

            {totalValidationIssues === 0 ? (
              <p className="success-text">Builder looks ready to save.</p>
            ) : (
              <div className="validation-list">
                {validation.examIssues.map((issue) => (
                  <p key={issue} className="validation-hint">
                    {issue}
                  </p>
                ))}
                {Object.entries(validation.questionIssues).flatMap(([, issues]) =>
                  issues.map((issue) => (
                    <p key={issue} className="validation-hint">
                      {issue}
                    </p>
                  )),
                )}
              </div>
            )}
          </section>
        </aside>
      </div>
    </section>
  );
}

export default ExamEditorPage;
