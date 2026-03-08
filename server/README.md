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

3. `POST /answers/autosave`
- Request:
```json
{
  "attempt_id":"<attempt-uuid>",
  "answers":[{"question_id":"<question-uuid>","answer_text":"Draft answer"}]
}
```
- Upserts answers by `(attempt_id, question_id)` and is idempotent for repeated saves.

4. `POST /answers/submit`
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

4. Autosave one answer:

```bash
curl -s -X POST http://127.0.0.1:8000/answers/autosave \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"attempt_id":"<attempt_uuid>","answers":[{"question_id":"<question_uuid>","answer_text":"My draft answer"}]}'
```

5. Submit answers:

```bash
curl -s -X POST http://127.0.0.1:8000/answers/submit \
  -H "Authorization: Bearer <student_token>" \
  -H "Content-Type: application/json" \
  -d '{"attempt_id":"<attempt_uuid>","answers":[{"question_id":"<question_uuid>","answer_text":"My final answer"}]}'
```
