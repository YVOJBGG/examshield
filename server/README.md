# ExamShield Server

## Prerequisites

- Python 3.11+
- Docker

## Setup

```bash
cd server
python -m venv .venv
```

Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local environment file from template:

```powershell
Copy-Item .env.example .env
```

## Start PostgreSQL

From `server/`:

```bash
docker compose up -d
```

## Run Migrations

From `server/`:

```bash
alembic upgrade head
```

## Seed Dev Data

From `server/`:

```bash
python -m app.scripts.seed
```

## Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
pytest
```

Milestone 2 exam-management tests:

```bash
pytest tests/test_exams_crud.py tests/test_questions_crud.py
```

Milestone 3 student exam-execution tests:

```bash
pytest tests/test_student_exam_execution.py
```

## Lint and Format

```bash
ruff check .
ruff check . --fix
black .
```

## Milestone 3 Student Exam Execution API

All endpoints below require a student bearer token and enforce `require_student`.
Admin tokens receive `403 {"detail":"Student access required"}`.

Duplicate active attempt behavior for `POST /attempts/start`:
- If the student already has an `in_progress` attempt for the same exam, the existing attempt is returned.
- No duplicate active attempt is created.

### Endpoints

1. `POST /attempts/start`
- Request:
```json
{"exam_id":"<exam-uuid>"}
```
- Response: `AttemptOut`

2. `GET /student/exams/{exam_id}`
- Response includes only student-safe exam data:
  - `id`, `title`, `time_limit_minutes`, `questions[{id,text}]`

3. `GET /student/exams`
- Response includes only student-safe exam list items:
  - `id`, `title`, `time_limit_minutes`

4. `POST /answers/autosave`
- Request:
```json
{
  "attempt_id":"<attempt-uuid>",
  "answers":[{"question_id":"<question-uuid>","answer_text":"Draft answer"}]
}
```
- Upserts answers by `(attempt_id, question_id)` and is idempotent for repeated saves.

5. `POST /answers/submit`
- Request is the same shape as autosave.
- Upserts final answers, sets attempt status to `submitted`, sets `submitted_at`, and returns:
```json
{
  "attempt": { "...": "AttemptOut fields" },
  "answers_saved": 1
}
```

### Error behavior

- `404` exam/attempt not found
- `403` attempt owned by another student
- `400` autosave/submit when attempt is no longer in progress
- `400` answer question does not belong to the attempt exam

## Quick curl flow (student)

Use `http://127.0.0.1:8000` in examples below.

1. Login as student:

```bash
curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"student123"}'
```

2. Start attempt:

```bash
curl -s -X POST http://127.0.0.1:8000/attempts/start \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"exam_id":"<exam_uuid>"}'
```

3. Fetch exam content:

```bash
curl -s http://127.0.0.1:8000/student/exams/<exam_uuid> \
  -H "Authorization: Bearer <student_token>"
```

4. List available exams:

```bash
curl -s http://127.0.0.1:8000/student/exams \
  -H "Authorization: Bearer <student_token>"
```

5. Autosave one answer:

```bash
curl -s -X POST http://127.0.0.1:8000/answers/autosave \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"attempt_id":"<attempt_uuid>","answers":[{"question_id":"<question_uuid>","answer_text":"My draft answer"}]}'
```

6. Submit answers:

```bash
curl -s -X POST http://127.0.0.1:8000/answers/submit \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"attempt_id":"<attempt_uuid>","answers":[{"question_id":"<question_uuid>","answer_text":"My final answer"}]}'
```

## Milestone 4 Live Monitoring API

Scope for this milestone:
- Real-time admin monitoring via WebSocket push (no polling required).
- Student status event ingest via REST and immediate broadcast to admins.
- In-memory active-attempt snapshot for fast dashboard initialization.
- No screenshot streaming, no violation alerts, no persistence for monitoring events.

### Endpoints

1. `GET ws://127.0.0.1:8000/ws/admin/monitor?token=<admin_jwt>`
- Auth: query `token` must be a valid admin JWT.
- On connect: server sends a snapshot message:
```json
{
  "type": "snapshot",
  "attempts": [
    {
      "attempt_id": "00000000-0000-0000-0000-000000000001",
      "username": "student1",
      "exam_id": "00000000-0000-0000-0000-000000000010",
      "status": "in_progress",
      "last_event": "autosave",
      "last_update": "2026-02-22T12:00:00Z"
    }
  ]
}
```
- Then receives event pushes:
```json
{
  "type": "event",
  "data": {
    "event_type": "in_exam",
    "timestamp": "2026-02-22T12:00:00Z",
    "user_id": "00000000-0000-0000-0000-000000000002",
    "username": "student1",
    "exam_id": "00000000-0000-0000-0000-000000000010",
    "attempt_id": "00000000-0000-0000-0000-000000000001",
    "status": "in_progress",
    "message": "Student started exam"
  }
}
```
- Invalid token or non-admin role: connection is closed with policy violation.

2. `POST /monitoring/status`
- Auth: student bearer token required (`require_student`).
- Allowed `event_type`: `connected`, `in_exam`, `autosave`, `submitted`, `disconnected`.
- Request:
```json
{
  "event_type": "autosave",
  "timestamp": "2026-02-22T12:01:00Z",
  "exam_id": "00000000-0000-0000-0000-000000000010",
  "attempt_id": "00000000-0000-0000-0000-000000000001",
  "status": "in_progress",
  "message": "Draft saved"
}
```
- Response: enriched event payload (adds `user_id`, `username`) and broadcasts to all connected admin sockets.

### Student sender example (curl)

```bash
curl -s -X POST http://127.0.0.1:8000/monitoring/status \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"in_exam","exam_id":"<exam_uuid>","attempt_id":"<attempt_uuid>","status":"in_progress","message":"Student started exam"}'
```

### Admin WebSocket example (minimal JavaScript)

```js
const token = "<admin_jwt>";
const ws = new WebSocket(`ws://127.0.0.1:8000/ws/admin/monitor?token=${encodeURIComponent(token)}`);

ws.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  if (payload.type === "snapshot") {
    console.log("Initial attempts:", payload.attempts);
  } else if (payload.type === "event") {
    console.log("Live event:", payload.data);
  }
};
```

## Milestone 5 Violations and Instant Alerts API

Scope for this milestone:
- Students can report violations tied to an active attempt.
- Violations are persisted in the database.
- Violations are broadcast live to connected admin dashboards.
- Monitoring snapshots now include `alert_count`, `has_alerts`, `last_violation_type`, and `last_violation_at`.

### Endpoints

1. `POST /violations`
- Auth: student bearer token required (`require_student`).
- Request:
```json
{
  "attempt_id": "00000000-0000-0000-0000-000000000001",
  "type": "focus_lost",
  "details": "Window lost focus during exam"
}
```
- Response `201`:
```json
{
  "id": "00000000-0000-0000-0000-000000000101",
  "attempt_id": "00000000-0000-0000-0000-000000000001",
  "type": "focus_lost",
  "details": "Window lost focus during exam",
  "created_at": "2026-03-18T10:15:00Z"
}
```
- Validation:
  - attempt must exist
  - attempt must belong to the authenticated student
  - attempt must still be `in_progress`
  - `type` must be non-empty

2. `GET /violations/attempt/{attempt_id}`
- Auth: admin bearer token required (`require_admin`).
- Response:
```json
[
  {
    "id": "00000000-0000-0000-0000-000000000101",
    "attempt_id": "00000000-0000-0000-0000-000000000001",
    "type": "focus_lost",
    "details": "Window lost focus during exam",
    "created_at": "2026-03-18T10:15:00Z"
  }
]
```

### Live admin broadcast

Every successful `POST /violations` call also pushes this message to all active admin monitor sockets:

```json
{
  "type": "violation",
  "data": {
    "id": "00000000-0000-0000-0000-000000000101",
    "attempt_id": "00000000-0000-0000-0000-000000000001",
    "type": "focus_lost",
    "details": "Window lost focus during exam",
    "created_at": "2026-03-18T10:15:00Z",
    "username": "student1",
    "exam_id": "00000000-0000-0000-0000-000000000010",
    "status": "in_progress"
  }
}
```

The broadcast is sent after the in-memory monitoring snapshot is updated, so newly connected admin dashboards immediately receive the correct alert metadata for active attempts.

### curl examples

Create a violation:

```bash
curl -s -X POST http://127.0.0.1:8000/violations \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "attempt_id":"<attempt_uuid>",
    "type":"focus_lost",
    "details":"Window lost focus during exam"
  }'
```

List one attempt's violations:

```bash
curl -s http://127.0.0.1:8000/violations/attempt/<attempt_uuid> \
  -H "Authorization: Bearer <admin_token>"
```

## Admin exam finalization and analytics

Scope for this feature:
- Admins can explicitly end one exam.
- Active attempts for that exam are force-submitted immediately.
- Analytics are available per exam from persisted attempts, answers, violations, screenshots, and question data.

### Endpoints

1. `POST /admin/exams/{exam_id}/end`
- Auth: admin bearer token required (`require_admin`).
- Behavior:
  - validates the exam exists
  - marks the exam as ended with `is_ended=true` and `ended_at=<now>`
  - updates all `in_progress` attempts for that exam to `force_submitted`
  - sets `submitted_at` for those attempts when missing
- Response:
```json
{
  "exam_id": "00000000-0000-0000-0000-000000000010",
  "ended_at": "2026-04-06T12:00:00Z",
  "updated_attempts": 12,
  "already_completed_attempts": 5,
  "status": "ended"
}
```

2. `GET /admin/exams/{exam_id}/analytics`
- Auth: admin bearer token required (`require_admin`).
- Response shape:
```json
{
  "exam": {
    "exam_id": "00000000-0000-0000-0000-000000000010",
    "exam_title": "Database Systems Midterm",
    "total_attempts": 18,
    "completed_attempts": 18,
    "force_submitted_attempts": 3,
    "submission_rate_percent": 100.0,
    "average_exam_duration_seconds": 2412.5,
    "min_exam_duration_seconds": 1800.0,
    "max_exam_duration_seconds": 2700.0,
    "median_exam_duration_seconds": 2400.0,
    "average_violations_per_attempt": 0.67,
    "total_violations": 12,
    "total_screenshots": 30,
    "most_common_violation_type": "focus_lost",
    "attempts_with_highest_violation_count": [
      {
        "attempt_id": "00000000-0000-0000-0000-000000000111",
        "username": "student7",
        "violation_count": 4
      }
    ],
    "average_questions_answered_per_attempt": 7.94,
    "attempts_with_violations_percent": 44.44,
    "hardest_question": {
      "question_id": "00000000-0000-0000-0000-000000000210",
      "question_text": "Which SQL clause filters rows?",
      "metric": "lowest_correct_rate_percent",
      "value": 52.94
    },
    "ended_at": "2026-04-06T12:00:00Z",
    "is_ended": true
  },
  "questions": [
    {
      "question_id": "00000000-0000-0000-0000-000000000210",
      "question_text": "Which SQL clause filters rows?",
      "average_time_spent_seconds": 133.2,
      "total_answers": 17,
      "unanswered_count": 1,
      "mcq_option_distribution": [
        {
          "option_id": "00000000-0000-0000-0000-000000000310",
          "option_text": "WHERE",
          "count": 9,
          "percentage": 52.94
        }
      ],
      "correct_rate_percent": 52.94
    }
  ],
  "metadata": {
    "question_time_method": "approx_saved_at_deltas",
    "question_alert_method": "not_available"
  }
}
```

### Approximation notes

- `question_time_method=approx_saved_at_deltas` means per-question time is estimated from answer `saved_at` ordering relative to `attempt.started_at`.
- The backend stores one current answer row per `(attempt_id, question_id)`, so this timing is an approximation from observed save timestamps rather than exact navigation telemetry.
- `question_alert_method=not_available` means violations are stored at attempt level only; the API does not invent exact per-question alert counts when the schema cannot support them.

### curl examples

End one exam:

```bash
curl -s -X POST http://127.0.0.1:8000/admin/exams/<exam_uuid>/end \
  -H "Authorization: Bearer <admin_token>"
```

Fetch analytics for one exam:

```bash
curl -s http://127.0.0.1:8000/admin/exams/<exam_uuid>/analytics \
  -H "Authorization: Bearer <admin_token>"
```
