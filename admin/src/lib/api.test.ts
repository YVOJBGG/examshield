import {
  ApiError,
  authFetch,
  clearToken,
  createExam,
  endExam,
  getExamAnalytics,
  setToken,
} from "./api";

describe("api client helpers", () => {
  it("adds the bearer token to authenticated requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    setToken("secret-token");

    await authFetch("/admin/exams/123/end", { method: "POST" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/exams/123/end",
      expect.objectContaining({
        method: "POST",
        headers: expect.any(Headers),
      }),
    );

    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer secret-token");

    clearToken();
  });

  it("throws a typed ApiError when ending an exam fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Exam not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(endExam("missing")).rejects.toEqual(new ApiError(404, "Exam not found"));
  });

  it("loads analytics data from the admin analytics endpoint", async () => {
    const payload = {
      exam: {
        exam_id: "exam-1",
        exam_title: "Networks Final",
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
        is_ended: true,
      },
      questions: [],
      metadata: {
        question_time_method: "approx_saved_at_deltas",
        question_alert_method: "not_available",
      },
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await getExamAnalytics("exam-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/admin/exams/exam-1/analytics",
      expect.objectContaining({ headers: expect.any(Headers) }),
    );
    expect(response).toEqual(payload);
  });

  it("rejects invalid exam creation payloads before sending the request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createExam({
        title: "Invalid exam",
        exam_type: "written",
        time_limit_minutes: 0,
      }),
    ).rejects.toEqual(new ApiError(400, "Time limit must be greater than 0."));

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
