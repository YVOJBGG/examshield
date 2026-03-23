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
  time_limit_minutes: number;
  is_available: boolean;
  created_at: string;
};

export type ExamCreate = {
  title: string;
  time_limit_minutes: number;
  is_available?: boolean;
};

export type ExamUpdate = Partial<ExamCreate>;

export type Question = {
  id: string;
  exam_id: string;
  text: string;
  created_at: string;
};

export type QuestionCreate = {
  text: string;
};

export type QuestionUpdate = Partial<QuestionCreate>;

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
};

export type AttemptReviewAnswer = {
  question_id: string;
  question_text: string;
  answer_text?: string | null;
};

export type AttemptReviewDetail = {
  attempt_id: string;
  status: string;
  started_at: string;
  submitted_at?: string | null;
  score?: number | null;
  graded_at?: string | null;
  student: {
    id: string;
    username: string;
  };
  exam: {
    id: string;
    exam_code: string;
    title: string;
  };
  answers: AttemptReviewAnswer[];
};

export type AttemptScoreOut = {
  id: string;
  status: string;
  submitted_at?: string | null;
  score?: number | null;
  graded_at?: string | null;
};

export type ScreenshotListItem = {
  id: string;
  attempt_id: string;
  file_path: string;
  captured_at: string;
  file_url: string;
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

export async function adminPing(): Promise<unknown> {
  const response = await authFetch("/admin/ping");
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, "Admin ping failed"));
  }

  return parseJson<unknown>(response);
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
