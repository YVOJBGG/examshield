const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "access_token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type MeResponse = {
  id: string;
  username: string;
  role: string;
};

export type Exam = {
  id: string;
  exam_code: string;
  title: string;
  exam_type: "mcq" | "written";
  time_limit_minutes: number;
  instructions?: string | null;
  is_available: boolean;
  is_ended: boolean;
  ended_at?: string | null;
  created_at: string;
};

export type ExamCreate = {
  title: string;
  exam_type: "mcq" | "written";
  time_limit_minutes: number;
  instructions?: string | null;
  is_available?: boolean;
};

export type ExamUpdate = Partial<ExamCreate>;

export type QuestionOption = {
  id: string;
  question_id: string;
  option_text: string;
  is_correct: boolean;
  order_index: number;
};

export type Question = {
  id: string;
  exam_id: string;
  text: string;
  points: number;
  order_index: number;
  options: QuestionOption[];
  created_at: string;
};

export type QuestionOptionCreate = {
  option_text: string;
  is_correct: boolean;
  order_index?: number;
};

export type QuestionCreate = {
  text: string;
  points: number;
  order_index?: number;
  options?: QuestionOptionCreate[];
};

export type QuestionUpdate = Partial<QuestionCreate>;

export type ExamDetail = Exam & {
  questions: Question[];
};

export type ViolationListItem = {
  id: string;
  attempt_id: string;
  type: string;
  details?: string | null;
  created_at: string;
};

export type ExamAttemptListItem = {
  attempt_id: string;
  username: string;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  score?: number | null;
  grading_state?: "pending_manual_grading" | "manually_graded" | "auto_graded";
};

export type AttemptReviewAnswer = {
  question_id: string;
  question_text: string;
  points: number;
  order_index: number;
  answer_text?: string | null;
  selected_option_ids?: string[];
  options?: Array<{
    id: string;
    option_text: string;
    order_index: number;
    is_correct: boolean;
  }>;
  is_correct?: boolean | null;
  awarded_points?: number | null;
};

export type AttemptReviewDetail = {
  attempt_id: string;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  score?: number | null;
  graded_at?: string | null;
  grading_state?: "pending_manual_grading" | "manually_graded" | "auto_graded";
  student: {
    id: string;
    username: string;
  };
  exam: {
    id: string;
    exam_code: string;
    title: string;
    exam_type: "mcq" | "written";
    instructions?: string | null;
  };
  answers: AttemptReviewAnswer[];
};

export type AttemptScoreOut = {
  id: string;
  status: string;
  submitted_at?: string | null;
  score?: number | null;
  graded_at?: string | null;
  grading_state?: "pending_manual_grading" | "manually_graded" | "auto_graded";
};

export type ScreenshotListItem = {
  id: string;
  attempt_id: string;
  file_path: string;
  captured_at: string;
  file_url: string;
};

export type EndExamResponse = {
  exam_id: string;
  ended_at: string;
  updated_attempts: number;
  already_completed_attempts: number;
  status: string;
};

export type ExamAnalyticsQuestionOption = {
  option_id: string;
  option_text: string;
  count: number;
  percentage: number;
};

export type ExamAnalyticsQuestion = {
  question_id: string;
  question_text: string;
  average_time_spent_seconds?: number;
  total_answers: number;
  unanswered_count: number;
  alert_count_for_question?: number | null;
  average_answer_length?: number;
  mcq_option_distribution?: ExamAnalyticsQuestionOption[];
  correct_rate_percent?: number;
};

export type ExamAnalyticsHighestViolationAttempt = {
  attempt_id: string;
  username?: string | null;
  violation_count: number;
};

export type ExamAnalyticsHardestQuestion = {
  question_id: string;
  question_text: string;
  metric: string;
  value: number;
};

export type ExamAnalyticsSummary = {
  exam_id: string;
  exam_title: string;
  total_attempts: number;
  completed_attempts: number;
  force_submitted_attempts: number;
  submission_rate_percent: number;
  average_exam_duration_seconds?: number;
  min_exam_duration_seconds?: number;
  max_exam_duration_seconds?: number;
  median_exam_duration_seconds?: number;
  average_violations_per_attempt: number;
  total_violations: number;
  total_screenshots: number;
  most_common_violation_type?: string | null;
  attempts_with_highest_violation_count: ExamAnalyticsHighestViolationAttempt[];
  average_questions_answered_per_attempt: number;
  attempts_with_violations_percent: number;
  hardest_question?: ExamAnalyticsHardestQuestion | null;
  ended_at?: string | null;
  is_ended: boolean;
};

export type ExamAnalyticsResponse = {
  exam: ExamAnalyticsSummary;
  questions: ExamAnalyticsQuestion[];
  metadata: {
    question_time_method: string;
    question_alert_method: string;
  };
};

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${API_BASE_URL}${input}`, { ...init, headers });
}

async function parseJson<T>(response: Response): Promise<T> {
  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null);
  if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
    return body.detail;
  }
  return fallback;
}

function ensurePositiveMinutes(minutes: number): void {
  if (minutes <= 0) {
    throw new ApiError(400, "Time limit must be greater than 0.");
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Login failed"));
  }

  return parseJson<LoginResponse>(response);
}

export async function getMe(): Promise<MeResponse> {
  const response = await authFetch("/auth/me");

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load current user"));
  }

  return parseJson<MeResponse>(response);
}

export async function listExams(): Promise<Exam[]> {
  const response = await authFetch("/exams");
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load exams"));
  }
  return parseJson<Exam[]>(response);
}

export async function createExam(payload: ExamCreate): Promise<Exam> {
  ensurePositiveMinutes(payload.time_limit_minutes);
  const response = await authFetch("/exams", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not create exam"));
  }
  return parseJson<Exam>(response);
}

export async function getExam(examId: string): Promise<Exam> {
  const response = await authFetch(`/exams/${examId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load exam"));
  }
  return parseJson<Exam>(response);
}

export async function getExamDetail(examId: string): Promise<ExamDetail> {
  const response = await authFetch(`/exams/${examId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load exam"));
  }
  return parseJson<ExamDetail>(response);
}

export async function updateExam(examId: string, payload: ExamUpdate): Promise<Exam> {
  if (payload.time_limit_minutes !== undefined) {
    ensurePositiveMinutes(payload.time_limit_minutes);
  }
  const response = await authFetch(`/exams/${examId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not update exam"));
  }
  return parseJson<Exam>(response);
}

export async function deleteExam(examId: string): Promise<void> {
  const response = await authFetch(`/exams/${examId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not delete exam"));
  }
}

export async function listQuestions(examId: string): Promise<Question[]> {
  const response = await authFetch(`/exams/${examId}/questions`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load questions"));
  }
  return parseJson<Question[]>(response);
}

export async function createQuestion(examId: string, payload: QuestionCreate): Promise<Question> {
  const response = await authFetch(`/exams/${examId}/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not create question"));
  }
  return parseJson<Question>(response);
}

export async function getQuestion(examId: string, questionId: string): Promise<Question> {
  const response = await authFetch(`/exams/${examId}/questions/${questionId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load question"));
  }
  return parseJson<Question>(response);
}

export async function updateQuestion(
  examId: string,
  questionId: string,
  payload: QuestionUpdate,
): Promise<Question> {
  const response = await authFetch(`/exams/${examId}/questions/${questionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not update question"));
  }
  return parseJson<Question>(response);
}

export async function deleteQuestion(examId: string, questionId: string): Promise<void> {
  const response = await authFetch(`/exams/${examId}/questions/${questionId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not delete question"));
  }
}

export async function listAttemptViolations(attemptId: string): Promise<ViolationListItem[]> {
  const response = await authFetch(`/violations/attempt/${attemptId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load violations"));
  }
  return parseJson<ViolationListItem[]>(response);
}

export async function listExamAttempts(examId: string): Promise<ExamAttemptListItem[]> {
  const response = await authFetch(`/admin/exams/${examId}/attempts`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load submissions"));
  }
  return parseJson<ExamAttemptListItem[]>(response);
}

export async function getAttemptReview(attemptId: string): Promise<AttemptReviewDetail> {
  const response = await authFetch(`/admin/attempts/${attemptId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load attempt review"));
  }
  return parseJson<AttemptReviewDetail>(response);
}

export async function saveAttemptScore(attemptId: string, score: number): Promise<AttemptScoreOut> {
  const response = await authFetch(`/admin/attempts/${attemptId}/score`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ score }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not save score"));
  }
  return parseJson<AttemptScoreOut>(response);
}

export async function listAttemptScreenshots(attemptId: string): Promise<ScreenshotListItem[]> {
  const response = await authFetch(`/screenshots/attempt/${attemptId}`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load screenshots"));
  }
  return parseJson<ScreenshotListItem[]>(response);
}

export async function getScreenshotBlob(screenshotId: string): Promise<Blob> {
  const response = await authFetch(`/screenshots/${screenshotId}/file`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load screenshot file"));
  }
  return response.blob();
}

export async function endExam(examId: string): Promise<EndExamResponse> {
  const response = await authFetch(`/admin/exams/${examId}/end`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not end exam"));
  }
  return parseJson<EndExamResponse>(response);
}

export async function getExamAnalytics(examId: string): Promise<ExamAnalyticsResponse> {
  const response = await authFetch(`/admin/exams/${examId}/analytics`);
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Could not load exam analytics"));
  }
  return parseJson<ExamAnalyticsResponse>(response);
}
