import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError, type EndExamResponse, type Exam } from "../lib/api";
import { renderWithRouter } from "../test/test-utils";
import ExamsListPage from "./ExamsListPage";

const mockNavigate = vi.fn();
const listExamsMock = vi.fn();
const deleteExamMock = vi.fn();
const endExamMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    listExams: (...args: unknown[]) => listExamsMock(...args),
    deleteExam: (...args: unknown[]) => deleteExamMock(...args),
    endExam: (...args: unknown[]) => endExamMock(...args),
  };
});

function makeExam(overrides: Partial<Exam> = {}): Exam {
  return {
    id: "exam-1",
    exam_code: "123456",
    title: "Database Systems",
    exam_type: "written",
    time_limit_minutes: 60,
    instructions: null,
    is_available: true,
    is_ended: false,
    ended_at: null,
    created_at: "2026-04-14T08:00:00Z",
    ...overrides,
  };
}

describe("ExamsListPage", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    listExamsMock.mockReset();
    deleteExamMock.mockReset();
    endExamMock.mockReset();
  });

  it("loads exams and shows the admin summary cards", async () => {
    listExamsMock.mockResolvedValue([
      makeExam(),
      makeExam({ id: "exam-2", exam_type: "mcq", title: "Networks", exam_code: "654321" }),
    ]);

    renderWithRouter(<ExamsListPage onAuthError={vi.fn()} />);

    expect(screen.getByText("Loading exams...")).toBeInTheDocument();
    expect(await screen.findByText("Database Systems")).toBeInTheDocument();
    expect(screen.getByText("Networks")).toBeInTheDocument();
    expect(screen.getByText("Total exams")).toBeInTheDocument();
    expect(screen.getAllByText("2")).toHaveLength(2);
  });

  it("ends an exam, disables the button while pending, and navigates to analytics", async () => {
    const user = userEvent.setup();
    const exam = makeExam();
    let resolveEnd: ((value: EndExamResponse) => void) | undefined;
    listExamsMock.mockResolvedValue([exam]);
    endExamMock.mockImplementation(
      () =>
        new Promise<EndExamResponse>((resolve) => {
          resolveEnd = resolve;
        }),
    );
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderWithRouter(<ExamsListPage onAuthError={vi.fn()} />);

    const button = await screen.findByRole("button", { name: "End Exam" });
    await user.click(button);

    expect(endExamMock).toHaveBeenCalledWith("exam-1");
    expect(screen.getByRole("button", { name: "Ending..." })).toBeDisabled();

    resolveEnd?.({
      exam_id: "exam-1",
      ended_at: "2026-04-14T10:30:00Z",
      updated_attempts: 2,
      already_completed_attempts: 1,
      status: "ended",
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/exams/exam-1/analytics", {
        state: {
          successMessage:
            "Exam ended successfully. 2 active attempts were submitted automatically.",
        },
      });
    });
  });

  it("surfaces authorization failures cleanly", async () => {
    const onAuthError = vi.fn();
    listExamsMock.mockRejectedValue(new ApiError(403, "Forbidden"));

    renderWithRouter(<ExamsListPage onAuthError={onAuthError} />);

    expect(await screen.findByText("Error: Forbidden")).toBeInTheDocument();
    expect(onAuthError).toHaveBeenCalledWith(
      "Authentication failed or insufficient permissions. Please login as admin.",
    );
  });
});
