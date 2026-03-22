# ExamShield Project Documentation (Source of Truth)

## A) Project Overview

ExamShield is an online exam integrity system with three applications:
- `admin/`: React admin portal for exam management and live monitoring.
- `server/`: FastAPI backend API, authentication, persistence, and WebSocket monitoring stream.
- `client/`: PyQt student desktop client for login, exam execution, autosave, monitoring, and minimal violation reporting.

System goals:
- Enforce secure exam behavior on the student side.
- Detect and record suspicious behavior as violations.
- Capture screenshots during attempts.
- Give admins visibility into active attempts and incidents.

Current project state:
- Milestone 0: Done.
- Milestone 1: Implemented baseline auth and project setup.
  - PostgreSQL + SQLAlchemy + Alembic migrations in place.
  - JWT auth implemented with `/auth/login` and `/auth/me`.
  - Role guards implemented for `admin` and `student`.
- Milestone 2: Implemented exam management.
  - Admin-only CRUD for exams and nested questions is implemented in backend and admin UI.
- Milestone 3: Implemented student exam execution.
  - Student exam fetch, attempt start, autosave, submit, and local cache are implemented.
  - Answer upsert flow is backed by a uniqueness migration for `(attempt_id, question_id)`.
- Milestone 4: Implemented live monitoring.
  - Student client sends monitoring status events.
  - Backend exposes admin monitoring WebSocket and in-memory snapshot state.
  - Admin UI shows live monitoring connection status and active attempt updates.
- Milestone 5: Implemented backend/client/admin violations and live alerts.
  - Student client can report best-effort violations.
  - Backend persists violations, validates attempt ownership/state, and broadcasts admin alerts.
  - Admin UI shows alert toasts, highlighted rows, alert filtering, and per-attempt violation history.

## B) Repository Structure (actual tree)

Repository root: `D:\ThesisProject\examshield`

```text
examshield/
|- admin/
|  |- src/
|  |  |- App.tsx
|  |  |- main.tsx
|  |  |- style.css
|  |  |- lib/
|  |  |  |- api.ts
|  |  |  `- monitoring.ts
|  |  `- pages/
|  |     |- ExamEditorPage.tsx
|  |     |- ExamsListPage.tsx
|  |     `- LiveMonitoringPage.tsx
|  |- .env(.example)
|  |- package.json
|  `- README.md
|- client/
|  |- app/
|  |  |- main.py
|  |  |- config.py
|  |  |- services/
|  |  |  |- auth_manager.py
|  |  |  |- monitoring_client.py
|  |  |  |- network_client.py
|  |  |  |- quiz_manager.py
|  |  |  `- violation_service.py
|  |  |- storage/
|  |  `- ui/
|  |     |- exam_window.py
|  |     `- login_window.py
|  |- app_data/
|  |- requirements.txt
|  `- README.md
|- docs/
|  |- diagrams/architecture.puml
|  |- srs/
|  `- PROJECT_DOCUMENTATION.md
|- server/
|  |- alembic/
|  |  |- env.py
|  |  `- versions/
|  |     |- 0001_initial_schema.py
|  |     `- 0002_answers_unique.py
|  |- app/
|  |  |- api/
|  |  |  |- deps.py
|  |  |  |- routers/
|  |  |  |  |- admin.py
|  |  |  |  |- answers.py
|  |  |  |  |- attempts.py
|  |  |  |  |- auth.py
|  |  |  |  |- exams.py
|  |  |  |  |- monitoring.py
|  |  |  |  |- student_exams.py
|  |  |  |  `- violations.py
|  |  |  `- v1/router.py
|  |  |- core/
|  |  |- db/
|  |  |- models/
|  |  |- schemas/
|  |  |- services/
|  |  |- scripts/seed.py
|  |  `- main.py
|  |- tests/
|  |  |- conftest.py
|  |  |- test_attempts_flow.py
|  |  |- test_auth.py
|  |  |- test_exams_crud.py
|  |  |- test_health.py
|  |  |- test_questions_crud.py
|  |  |- test_student_exam_execution.py
|  |  `- test_violations.py
|  |- docker-compose.yml
|  |- alembic.ini
|  |- requirements.txt
|  `- README.md
`- README.md
```

Purpose of top-level folders:
- `server/`: backend API, DB schema/migrations, business logic, and tests.
- `admin/`: admin SPA for exams and live monitoring.
- `client/`: PyQt student client with exam execution, autosave, monitoring, and minimal violation reporting.
- `docs/`: architecture, SRS artifacts, and this canonical reference.

## C) Functional Requirements (FR) + Nonfunctional (NFR)

Priority order:
- P0 = MVP must-have
- P1 = core expansion
- P2 = reporting and optimization

Functional requirements:
- FR-01 Auth (P0)
  - Login and role-based access (`admin`, `student`).
  - Current: implemented and in use.

- FR-02 Lockdown (P0)
  - Student restrictions during active attempt.
  - Current: not implemented yet.
  - Planned approach: client `LockdownManager`.

- FR-03 Screenshots (P0)
  - Capture screenshot evidence during attempt.
  - Current: backend data model exists; end-to-end feature not implemented yet.

- FR-04 Cheating detection (P0)
  - Detect focus loss/forbidden actions and persist violations.
  - Current: minimally implemented end-to-end.
  - Implemented triggers:
    - `focus_lost`
    - `manual_flag` (dev/debug trigger)
  - Full OS-level detection remains later work.

- FR-05 Exam start (P0)
  - Student starts exam and gets active attempt.
  - Current: implemented with `POST /attempts/start`.

- FR-06 Answer autosave (P0)
  - Persist answers continuously.
  - Current: implemented with autosave/submit endpoints and client local cache fallback.

- FR-07 Exam management (P1)
  - Admin create/manage exams and questions.
  - Current: implemented in backend and admin UI.

- FR-08 Live monitor (P1)
  - Real-time admin view of attempts and violations.
  - Current: implemented with WebSocket snapshot/event stream and live admin dashboard.

- FR-09 Alerts (P1)
  - Notify admins on suspicious behavior.
  - Current: basic implementation complete.
  - Violations trigger live admin toast notifications, alert counters, highlighted rows, and violation history panel.

- FR-10 Reports (P2)
  - Export incident/attempt reports post exam.
  - Current: not implemented yet.

Nonfunctional requirements:
- NFR-01 Real-time latency under 2s for monitor updates.
  - Current approach: WebSocket push channel for monitoring and violation alerts.
- NFR-02 Security and least privilege.
  - Current approach: JWT auth, strict role guards, minimal token claims.
- NFR-03 Auditability.
  - Current approach: timestamped attempts, answers, violations, and screenshots schema.
- NFR-04 Offline caching.
  - Current approach: client local JSON cache with retry behavior for answers.
- NFR-05 Reliability.
  - Current approach: transactional writes, idempotent attempt start, answer upsert, best-effort monitoring/violation reporting on client.
- NFR-06 Maintainability.
  - Current approach: layered backend modules and split frontend/client service boundaries.
- NFR-07 Performance baseline.
  - Current approach: FK indexes plus unique constraint on answers per attempt/question.
- NFR-08 Portability.
  - Current approach: env-based configuration and dockerized local Postgres.

## D) Use Cases + Main User Flows

UC-1 Student takes exam:
1. Student signs in from PyQt client.
2. Student enters assigned exam ID.
3. Client loads student-safe exam content.
4. Client calls attempt start endpoint.
5. Exam window opens.
6. Student answers are cached locally on change.
7. Autosave runs periodically or manually.
8. Client emits monitoring events during the attempt.
9. Client emits best-effort violation events on focus loss or manual trigger.
10. Student submits attempt.

UC-2 Admin monitors exam:
1. Admin logs in to React admin portal.
2. Admin opens `/monitoring`.
3. Dashboard connects to WebSocket and receives snapshot.
4. Attempt updates stream live.
5. Violation alerts appear as toast + highlighted rows.
6. Admin filters to alerted attempts if needed.
7. Admin opens a violation history panel for a specific attempt.

## E) Architecture

High-level summary:
- Admin SPA talks to backend REST and admin monitoring WebSocket.
- Student client talks to backend REST for auth, exam fetch, attempts, answers, monitoring, and violations.
- Backend persists to PostgreSQL and keeps an in-memory monitoring snapshot for active attempts.

Component interactions:
- REST:
  - `/auth`
  - `/exams`
  - `/student/exams`
  - `/attempts/start`
  - `/answers/autosave`
  - `/answers/submit`
  - `/monitoring/status`
  - `/violations`
- WebSocket:
  - `/ws/admin/monitor?token=<admin_jwt>`

Text data flow:
- Login:
  - Admin or student -> `POST /auth/login` -> JWT returned.
- Student exam execution:
  - Student client -> load exam -> start attempt -> autosave/submit answers -> DB.
- Monitoring:
  - Student client -> `POST /monitoring/status` -> backend updates in-memory snapshot -> admin WebSocket receives `snapshot`/`event`.
- Violations:
  - Student client -> `POST /violations` -> violation row stored -> monitoring snapshot updated -> admin WebSocket receives `violation`.

Security boundaries:
- JWT bearer required on protected endpoints.
- `require_admin` for admin-only routes and monitor socket.
- `require_student` for student actions.
- Students may only report violations for their own active attempts.

## F) Data Model (ERD -> actual tables)

Schema sources:
- ORM models: `server/app/models/*.py`
- Migrations:
  - `server/alembic/versions/0001_initial_schema.py`
  - `server/alembic/versions/0002_answers_unique.py`

All primary keys are UUID and server generated.

`users`
- Fields: `id`, `username`, `password_hash`, `role`, `created_at`
- Constraints: unique username, role check (`admin|student`)
- Indexes: username
- Relation: one-to-many `users -> attempts`

`exams`
- Fields: `id`, `title`, `time_limit_minutes`, `created_at`
- Constraints: unique title
- Relations: one-to-many `exams -> questions`, `exams -> attempts`

`questions`
- Fields: `id`, `exam_id`, `text`, `created_at`
- FK: `exam_id -> exams.id`
- Indexes: exam_id
- Relation: one-to-many `questions -> answers`

`attempts`
- Fields: `id`, `user_id`, `exam_id`, `started_at`, `submitted_at`, `status`
- FKs: `user_id -> users.id`, `exam_id -> exams.id`
- Constraints: status check (`in_progress|submitted|cancelled`)
- Indexes: user_id, exam_id
- Relations: one-to-many to `answers`, `violations`, `screenshots`

`answers`
- Fields: `id`, `attempt_id`, `question_id`, `answer_text`, `saved_at`
- FKs: `attempt_id -> attempts.id`, `question_id -> questions.id`
- Indexes: attempt_id, question_id
- Constraints:
  - unique `(attempt_id, question_id)` from migration `0002_answers_unique`

`violations`
- Fields: `id`, `attempt_id`, `type`, `details`, `created_at`
- FK: `attempt_id -> attempts.id`
- Index: attempt_id

`screenshots`
- Fields: `id`, `attempt_id`, `file_path`, `captured_at`
- FK: `attempt_id -> attempts.id`
- Index: attempt_id

Screenshot storage strategy:
- DB stores metadata and `file_path`.
- End-to-end screenshot upload/capture is still pending.

## G) API Contracts (very important)

Base URL (dev): `http://localhost:8000` or `http://127.0.0.1:8000`

Auth:
- Header: `Authorization: Bearer <token>`

Implemented endpoints:

Auth:
- `POST /auth/login`
- `GET /auth/me`

Admin utility:
- `GET /admin/ping`

Exams and Questions (admin-only):
- `GET /exams`
- `POST /exams`
- `GET /exams/{exam_id}`
- `PUT /exams/{exam_id}`
- `DELETE /exams/{exam_id}`
- `GET /exams/{exam_id}/questions`
- `POST /exams/{exam_id}/questions`
- `GET /exams/{exam_id}/questions/{question_id}`
- `PUT /exams/{exam_id}/questions/{question_id}`
- `DELETE /exams/{exam_id}/questions/{question_id}`

Student exam execution:
- `GET /student/exams`
- `GET /student/exams/{exam_id}`
- `POST /attempts/start`
- `POST /answers/autosave`
- `POST /answers/submit`

Monitoring:
- `POST /monitoring/status` (student)
- `GET ws://<host>/ws/admin/monitor?token=<admin_jwt>` (admin socket)

Violations:
- `POST /violations` (student)
- `GET /violations/attempt/{attempt_id}` (admin)

Still planned:
- screenshots upload/list endpoints
- reports endpoints
- richer attempts list/detail endpoints for admin workflows

Key validation/authorization behavior:
- Non-admin on admin endpoints: `403 {"detail":"Admin access required"}`
- Non-student on student endpoints: `403 {"detail":"Student access required"}`
- Students cannot act on another student's attempt.
- Violations require attempt ownership and active `in_progress` status.
- Autosave/submit reject attempts that are no longer active.

Sample implemented request/response shapes:

`POST /attempts/start`
```json
{"exam_id":"<uuid>"}
```

`POST /answers/autosave`
```json
{
  "attempt_id":"<uuid>",
  "answers":[
    {"question_id":"<uuid>","answer_text":"Draft answer"}
  ]
}
```

`POST /answers/submit`
```json
{
  "attempt_id":"<uuid>",
  "answers":[
    {"question_id":"<uuid>","answer_text":"Final answer"}
  ]
}
```

`POST /violations`
```json
{
  "attempt_id":"<uuid>",
  "type":"focus_lost",
  "details":"Window lost focus during exam"
}
```

`GET /violations/attempt/{attempt_id}`
```json
[
  {
    "id":"<uuid>",
    "attempt_id":"<uuid>",
    "type":"focus_lost",
    "details":"Window lost focus during exam",
    "created_at":"2026-03-18T10:15:00Z"
  }
]
```

Standard error responses:
- `400` domain/validation error
- `401` unauthorized
- `403` forbidden
- `404` not found
- `422` schema validation error
- `500` internal server error

WebSocket contract (implemented):
- URL: `ws://<host>/ws/admin/monitor?token=<admin_jwt>`
- Auth: admin JWT in query param

Snapshot message:
```json
{
  "type":"snapshot",
  "attempts":[
    {
      "attempt_id":"<uuid>",
      "username":"student1",
      "exam_id":"<uuid>",
      "status":"in_progress",
      "last_event":"autosave",
      "last_update":"2026-03-18T10:10:00Z",
      "alert_count":1,
      "has_alerts":true,
      "last_violation_type":"focus_lost",
      "last_violation_at":"2026-03-18T10:09:00Z"
    }
  ]
}
```

Monitoring event message:
```json
{
  "type":"event",
  "data":{
    "event_type":"in_exam",
    "timestamp":"2026-03-18T10:10:00Z",
    "user_id":"<uuid>",
    "username":"student1",
    "exam_id":"<uuid>",
    "attempt_id":"<uuid>",
    "status":"in_progress",
    "message":"Student entered exam window"
  }
}
```

Violation alert message:
```json
{
  "type":"violation",
  "data":{
    "id":"<uuid>",
    "attempt_id":"<uuid>",
    "type":"focus_lost",
    "details":"Window lost focus during exam",
    "created_at":"2026-03-18T10:15:00Z",
    "username":"student1",
    "exam_id":"<uuid>",
    "status":"in_progress"
  }
}
```

## H) Client Apps Behavior

Admin portal (`admin/`):
- Login form stores bearer token in `localStorage`.
- Navigation currently exposes:
  - `/` for exams management
  - `/monitoring` for live monitoring
- Exams UI supports CRUD for exams and questions.
- Monitoring UI behavior:
  - connects to admin monitor WebSocket automatically
  - initializes rows from backend snapshot
  - handles live `event` and `violation` messages
  - shows connection indicator and last message timestamp
  - highlights alerted rows
  - shows alert count and latest violation type
  - supports `Show only attempts with alerts`
  - shows lightweight toast notifications on new violations
  - loads per-attempt violations panel via REST

Student client (`client/`):
- Current screens:
  - login window
  - active exam window
- Current services:
  - `AuthManager`
  - `NetworkClient`
  - `QuizManager`
  - `MonitoringClient`
  - `ViolationService`
  - local cache storage
- Current runtime behavior:
  - login with username/password + exam UUID
  - load exam and start or reuse active attempt
  - cache answers locally on change
  - autosave periodically and manually
  - submit answers
  - send monitoring events: `connected`, `in_exam`, `autosave`, `submitted`, `disconnected`, heartbeat
  - send best-effort violation events:
    - `focus_lost` on exam window deactivation
    - `manual_flag` from dev-only debug button
  - throttle repeated `focus_lost` reports with a 5-second cooldown
- Not yet implemented:
  - full lockdown
  - screenshot capture
  - advanced OS-level monitoring

## I) Environment & Configuration

Server env vars (`server/.env`, `server/app/core/config.py`):
- `APP_NAME`
- `ENV`
- `HOST`
- `PORT`
- `LOG_LEVEL`
- `DATABASE_URL`
- `DATABASE_URL_TEST`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRES_MINUTES`

Admin env vars (`admin/.env`):
- `VITE_API_BASE_URL`

Client env vars:
- `EXAMSHIELD_API_BASE_URL`
- `EXAMSHIELD_DEV_MODE`

Example values:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
EXAMSHIELD_API_BASE_URL=http://127.0.0.1:8000
EXAMSHIELD_DEV_MODE=1
```

Dev vs prod:
- Dev: local Postgres via `server/docker-compose.yml`, localhost API URLs, Vite dev server, PyQt client against local backend.
- Prod: managed DB, HTTPS, strict CORS, stronger secret management, and packaging/distribution for the client.

## J) Development Workflow

Run locally:

Server:
```bash
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Admin:
```bash
cd admin
npm install
npm run dev
```

Client:
```bash
cd client
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main
```

Server tests:
```bash
cd server
pytest
```

Targeted test notes:
- `tests/test_exams_crud.py` and `tests/test_questions_crud.py`: Milestone 2
- `tests/test_attempts_flow.py` and `tests/test_student_exam_execution.py`: Milestone 3
- `tests/test_violations.py`: Milestone 5 backend violations + WebSocket smoke coverage

Formatting/lint:
- Python: `black`, `ruff`
- Admin frontend: `npx tsc --noEmit`, `npm run build`

Coding conventions:
- Python:
  - snake_case modules/functions
  - PascalCase classes
  - routers call services; services interact with models/db
- TypeScript/React:
  - shared API logic in `admin/src/lib`
  - page-level UI in `admin/src/pages`
  - PascalCase components, camelCase helpers

## K) "How to Reference This Doc" Section

Instruction template:

> When implementing new tasks, do not scan the repository. Use `docs/PROJECT_DOCUMENTATION.md` as the source of truth and only open files that need changes.
