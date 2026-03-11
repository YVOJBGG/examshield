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
