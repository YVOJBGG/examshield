import { screen } from "@testing-library/react";

import { ApiError } from "../lib/api";
import { renderWithRouter } from "../test/test-utils";
import ExamAnalyticsPage from "./ExamAnalyticsPage";

const getExamMock = vi.fn();
const getExamAnalyticsMock = vi.fn();

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    getExam: (...args: unknown[]) => getExamMock(...args),
    getExamAnalytics: (...args: unknown[]) => getExamAnalyticsMock(...args),
  };
});

describe("ExamAnalyticsPage", () => {
  beforeEach(() => {
    getExamMock.mockReset();
    getExamAnalyticsMock.mockReset();
  });

  it("renders analytics sections, interpreted insights, and MCQ distributions", async () => {
    getExamMock.mockResolvedValue({
      id: "exam-1",
      exam_code: "123456",
      title: "Networks Final",
      exam_type: "mcq",
      time_limit_minutes: 45,
      instructions: null,
      is_available: false,
      is_ended: true,
      ended_at: "2026-04-14T10:30:00Z",
      created_at: "2026-04-14T08:00:00Z",
    });
    getExamAnalyticsMock.mockResolvedValue({
      exam: {
        exam_id: "exam-1",
        exam_title: "Networks Final",
        total_attempts: 4,
        completed_attempts: 4,
        force_submitted_attempts: 1,
        submission_rate_percent: 100,
        average_exam_duration_seconds: 1800,
        min_exam_duration_seconds: 1200,
        max_exam_duration_seconds: 2100,
        median_exam_duration_seconds: 1750,
        average_violations_per_attempt: 1.25,
        total_violations: 5,
        total_screenshots: 12,
        most_common_violation_type: "focus_lost",
        attempts_with_highest_violation_count: [
          { attempt_id: "attempt-1", username: "student1", violation_count: 3 },
        ],
        average_questions_answered_per_attempt: 9.5,
        attempts_with_violations_percent: 75,
        hardest_question: {
          question_id: "q-1",
          question_text: "Which protocol establishes reliable transport?",
          metric: "lowest_correct_rate_percent",
          value: 42,
        },
        ended_at: "2026-04-14T10:30:00Z",
        is_ended: true,
      },
      questions: [
        {
          question_id: "q-1",
          question_text: "Which protocol establishes reliable transport?",
          average_time_spent_seconds: 150,
          total_answers: 4,
          unanswered_count: 1,
          alert_count_for_question: null,
          mcq_option_distribution: [
            { option_id: "o-1", option_text: "TCP", count: 2, percentage: 50 },
            { option_id: "o-2", option_text: "UDP", count: 2, percentage: 50 },
          ],
          correct_rate_percent: 50,
        },
      ],
      metadata: {
        question_time_method: "approx_saved_at_deltas",
        question_alert_method: "not_available",
      },
    });

    renderWithRouter(<ExamAnalyticsPage onAuthError={vi.fn()} />, {
      path: "/exams/:examId/analytics",
      route: "/exams/exam-1/analytics",
    });

    expect(await screen.findByText("Networks Final analytics")).toBeInTheDocument();
    expect(screen.getByText("Additional insights")).toBeInTheDocument();
    expect(screen.getByText("Top flagged attempt")).toBeInTheDocument();
    expect(screen.getByText("Option distribution")).toBeInTheDocument();
    expect(screen.getByText("TCP")).toBeInTheDocument();
    expect(screen.getByText("Correct rate: 50%")).toBeInTheDocument();
  });

  it("shows a friendly empty state when the exam has no attempts", async () => {
    getExamMock.mockResolvedValue({
      id: "exam-2",
      exam_code: "999999",
      title: "Fresh Exam",
      exam_type: "written",
      time_limit_minutes: 30,
      instructions: null,
      is_available: true,
      is_ended: false,
      ended_at: null,
      created_at: "2026-04-14T08:00:00Z",
    });
    getExamAnalyticsMock.mockResolvedValue({
      exam: {
        exam_id: "exam-2",
        exam_title: "Fresh Exam",
        total_attempts: 0,
        completed_attempts: 0,
        force_submitted_attempts: 0,
        submission_rate_percent: 0,
        average_violations_per_attempt: 0,
        total_violations: 0,
        total_screenshots: 0,
        attempts_with_highest_violation_count: [],
        average_questions_answered_per_attempt: 0,
        attempts_with_violations_percent: 0,
        ended_at: null,
        is_ended: false,
      },
      questions: [],
      metadata: {
        question_time_method: "approx_saved_at_deltas",
        question_alert_method: "not_available",
      },
    });

    renderWithRouter(<ExamAnalyticsPage onAuthError={vi.fn()} />, {
      path: "/exams/:examId/analytics",
      route: "/exams/exam-2/analytics",
    });

    expect(await screen.findByText("No analytics yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This exam does not have any attempts yet, so there are no outcomes or monitoring patterns to summarize.",
      ),
    ).toBeInTheDocument();
  });

  it("shows backend errors and reports auth failures", async () => {
    const onAuthError = vi.fn();
    getExamMock.mockRejectedValue(new ApiError(403, "Forbidden"));
    getExamAnalyticsMock.mockResolvedValue(undefined);

    renderWithRouter(<ExamAnalyticsPage onAuthError={onAuthError} />, {
      path: "/exams/:examId/analytics",
      route: "/exams/exam-3/analytics",
    });

    expect(await screen.findByText("Error: Forbidden")).toBeInTheDocument();
    expect(onAuthError).toHaveBeenCalledWith(
      "Authentication failed or insufficient permissions. Please login as admin.",
    );
  });
});
