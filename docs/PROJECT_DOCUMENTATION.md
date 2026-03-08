# ExamShield Project Documentation (Source of Truth)

## A) Project Overview

ExamShield is an online exam integrity system with three applications:
- `admin/`: React admin portal for exam management and monitoring.
- `server/`: FastAPI backend API, authentication, and persistence.
- `client/`: Student desktop client workspace (PyQt planned, scaffold only).

System goals:
- Enforce secure exam behavior (lockdown on student side).
- Detect and record suspicious behavior as violations.
- Capture screenshots during attempts.
- Give admins visibility into active attempts and incidents.

Current project state:
- Milestone 0: Done (project setup and runnable scaffold).
- Milestone 1: Planned/starting, with partial implementation already present:
  - PostgreSQL + SQLAlchemy + Alembic initial migration implemented.
  - FR-01 JWT auth baseline implemented (`/auth/login`, `/auth/me`, role guards).
  - Minimal admin login validation UI implemented.
- Milestone 2: Started, backend FR-07 implemented:
  - Admin-only CRUD for `exams` and nested `questions` implemented in API.
  - Service layer + Pydantic schemas added for exam/question management.
  - Remaining FR modules are planned (see sections C, G, H).

## B) Repository Structure (actual tree)

Repository root: `D:\ThesisProject\examshield`

```text
examshield/
|- admin/
|  |- src/
|  |  |- App.tsx
|  |  |- main.tsx
|  |  |- style.css
|  |  `- lib/api.ts
|  |- .env(.example)
|  |- package.json
|  `- README.md
|- client/
|  `- app/                     # student app workspace (minimal currently)
|- docs/
|  |- diagrams/architecture.puml
|  |- srs/
|  `- PROJECT_DOCUMENTATION.md
|- server/
|  |- alembic/
|  |  |- env.py
|  |  `- versions/0001_initial_schema.py
|  |- app/
|  |  |- api/
|  |  |  |- deps.py
|  |  |  |- routers/
|  |  |  |  |- auth.py
|  |  |  |  `- admin.py
|  |  |  |  `- exams.py
|  |  |  `- v1/router.py
|  |  |- core/
|  |  |  |- config.py
|  |  |  `- security.py
|  |  |- db/
|  |  |  |- base.py
|  |  |  `- session.py
|  |  |- models/
|  |  |  |- user.py
|  |  |  |- exam.py
|  |  |  |- question.py
|  |  |  |- attempt.py
|  |  |  |- answer.py
|  |  |  |- violation.py
|  |  |  `- screenshot.py
|  |  |- schemas/
|  |  |- services/
|  |  |- scripts/seed.py
|  |  `- main.py
|  |- tests/
|  |  |- conftest.py
|  |  |- test_health.py
|  |  `- test_auth.py
|  |  |- test_exams_crud.py
|  |  `- test_questions_crud.py
|  |- docker-compose.yml
|  |- alembic.ini
|  |- requirements.txt
|  `- README.md
`- README.md
```

Purpose of top-level folders:
- `server/`: backend API, DB schema/migrations, business logic, tests.
- `admin/`: admin web app and frontend API client code.
- `client/`: student desktop app workspace (implementation pending).
- `docs/`: architecture, SRS materials, and this source-of-truth document.

Server app layout (`server/app`):
- `core`: settings and security primitives.
- `db`: SQLAlchemy base/session.
- `models`: database entities and relations.
- `schemas`: Pydantic request/response contracts.
- `services`: business service layer.
- `api`: route handlers and auth dependencies.
- `scripts`: operational scripts (seed).
- `tests` (outside app): integration and behavior tests.

Admin source layout (`admin/src`):
- Current: `App.tsx`, `main.tsx`, `style.css`, `lib/api.ts`.
- Planned growth: `pages/`, `components/`, `lib/`.
- To confirm: final route/page split after dashboard expansion.

Docs usage:
- `docs/srs/`: requirements artifacts.
- `docs/diagrams/`: architecture diagrams.
- `docs/PROJECT_DOCUMENTATION.md`: canonical engineering reference.

## C) Functional Requirements (FR) + Nonfunctional (NFR)

Priority order:
- P0 = MVP must-have
- P1 = core expansion
- P2 = reporting and optimization

Functional requirements:
- FR-01 Auth (P0)
  - Login and role-based access (`admin`, `student`).
  - Approach: bcrypt password hashes + JWT claims (`sub`, `role`, `username`, `exp`).
  - Current: partially implemented and in use.

- FR-02 Lockdown (P0)
  - Student restrictions during active attempt.
  - Approach: client `LockdownManager` service.
  - To confirm: exact OS-level restrictions and exceptions.

- FR-03 Screenshots (P0)
  - Capture screenshot evidence during attempt.
  - Approach: client screenshot service + backend metadata persistence.

- FR-04 Cheating detection (P0)
  - Detect focus loss/forbidden actions and persist violations.
  - Approach: client event detection + `violations` API.

- FR-05 Exam start (P0)
  - Student starts exam and gets active attempt.
  - Approach: attempts API creates row in `attempts`.

- FR-06 Answer autosave (P0)
  - Persist answers continuously.
  - Approach: answer save API + offline queue retry.

- FR-07 Exam management (P1)
  - Admin create/manage exams and questions.
  - Approach: exams/questions CRUD endpoints + admin pages.
  - Current: backend CRUD implemented (admin-only) and covered by dedicated API tests; admin UI pages still pending.

- FR-08 Live monitor (P1)
  - Real-time admin view of attempts and violations.
  - Approach: WebSocket stream + REST fallback query.

- FR-09 Alerts (P1)
  - Notify admins on high-risk behavior.
  - Approach: rule-based event aggregation and alert events.

- FR-10 Reports (P2)
  - Export incident/attempt reports post exam.
  - Approach: reports endpoints and summary generation.

Nonfunctional requirements:
- NFR-01 Real-time latency under 2s for monitor updates.
  - Approach: WebSocket push channel.
- NFR-02 Security and least privilege.
  - Approach: JWT auth, strict role guards, minimal token claims.
- NFR-03 Auditability.
  - Approach: timestamped attempts/answers/violations/screenshots.
- NFR-04 Offline caching.
  - Approach: client `OfflineQueue` with retry policy.
- NFR-05 Reliability.
  - Approach: transactional writes, idempotent seed and safe retries.
- NFR-06 Maintainability.
  - Approach: layered backend and module boundaries.
- NFR-07 Performance baseline.
  - Approach: FK indexes, paginated list endpoints.
- NFR-08 Portability.
  - Approach: env-based config + dockerized local Postgres.

## D) Use Cases + Main User Flows

UC-1 Student takes exam:
1. Student signs in.
2. Student selects/receives exam assignment.
3. Client calls start attempt endpoint.
4. Lockdown activates.
5. Questions load and student answers.
6. Autosave runs periodically and on edits.
7. Client emits violations and screenshot events.
8. Offline queue buffers failed sends and retries.
9. Student submits attempt.
10. Admin later reviews activity/report.

UC-2 Admin monitors exam:
1. Admin logs in.
2. Admin opens monitor dashboard.
3. Dashboard subscribes to real-time stream (or polls).
4. Attempt updates and violations appear.
5. Alerts are shown for suspicious activity.
6. Admin drills into specific attempt.
7. Admin exports/reviews report after exam.

## E) Architecture

High-level summary:
- Frontend admin SPA talks to backend REST and planned WebSocket channel.
- Backend enforces auth/roles and persists to PostgreSQL.
- Planned student client produces attempt/answer/violation/screenshot events.

Component interactions:
- REST for CRUD/actions (`/auth`, `/exams`, planned `/attempts`, `/answers`, etc.).
- WebSocket for live monitor updates (planned).

Text data flow:
- Login:
  - Admin or student -> `POST /auth/login` -> verify user hash -> JWT returned.
- Attempt execution:
  - Student client -> attempt start -> answer autosave and incident events -> DB.
- Monitoring:
  - Backend event persisted -> monitor stream emits update -> admin UI refreshes.

Security boundaries:
- JWT bearer required on protected endpoints.
- Role guards:
  - `require_admin`
  - `require_student`
- Password hashes only (bcrypt via passlib).

## F) Data Model (ERD -> actual tables)

Schema source:
- ORM models: `server/app/models/*.py`
- Migration: `server/alembic/versions/0001_initial_schema.py`

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

`violations`
- Fields: `id`, `attempt_id`, `type`, `details`, `created_at`
- FK: `attempt_id -> attempts.id`
- Index: attempt_id

`screenshots`
- Fields: `id`, `attempt_id`, `file_path`, `captured_at`
- FK: `attempt_id -> attempts.id`
- Index: attempt_id

Screenshot storage strategy:
- Binary image file stored outside DB.
- DB stores metadata and `file_path`.
- To confirm: production storage target (local volume vs object storage).

## G) API Contracts (very important)

Base URL (dev): `http://localhost:8000` or `http://127.0.0.1:8000`

Auth:
- Header: `Authorization: Bearer <token>`

Auth module (implemented):

1. `POST /auth/login`
- Auth required: no
- Roles: N/A
- Request:
```json
{"username":"admin","password":"admin123"}
```
- Response 200:
```json
{"access_token":"<jwt>","token_type":"bearer"}
```
- Errors:
  - 401 invalid credentials

2. `GET /auth/me`
- Auth required: yes
- Roles: admin, student
- Response 200:
```json
{"id":"<uuid>","username":"admin","role":"admin"}
```
- Errors:
  - 401 invalid/missing token

Admin module (implemented demo):

1. `GET /admin/ping`
- Auth required: yes
- Roles: admin only
- Response 200:
```json
{"status":"ok","message":"admin pong"}
```
- Errors:
  - 403 admin role required
  - 401 invalid/missing token

Implemented module and endpoint contracts:

Exams and Questions module (implemented, admin-only):
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

Auth and roles:
- Auth required: yes
- Allowed role: `admin` only
- Non-admin response: `403 {"detail":"Admin access required"}`
- Common not found responses:
  - `404 {"detail":"Exam not found"}`
  - `404 {"detail":"Question not found"}`
- Common validation response:
  - `400` for invalid input (`time_limit_minutes <= 0`, empty question text)

Cascade behavior:
- `DELETE /exams/{exam_id}` removes related questions via ORM/DB cascade (`Exam.questions` relationship and FK cascade).

Planned modules and endpoint contracts:

Attempts (planned):
- `POST /attempts/start` (student)
- `POST /attempts/{attempt_id}/submit` (student)
- `GET /attempts/{attempt_id}` (owner/admin)
- `GET /attempts` (admin filtered list)

Answers (planned):
- `PUT /attempts/{attempt_id}/answers/{question_id}` (student)
- `GET /attempts/{attempt_id}/answers` (owner/admin)

Violations (planned):
- `POST /attempts/{attempt_id}/violations` (student client)
- `GET /attempts/{attempt_id}/violations` (admin, owner optional)

Screenshots (planned):
- `POST /attempts/{attempt_id}/screenshots` (student client)
- `GET /attempts/{attempt_id}/screenshots` (admin)

Reports (planned):
- `GET /reports/attempts/{attempt_id}` (admin)
- `GET /reports/exams/{exam_id}` (admin)

Planned request/response examples:

Exam create request:
```json
{"title":"Midterm - CS101","time_limit_minutes":60}
```

Exam create response:
```json
{"id":"<uuid>","title":"Midterm - CS101","time_limit_minutes":60,"created_at":"2026-02-22T11:00:00Z"}
```

Answer save request:
```json
{"answer_text":"My answer"}
```

Violation create request:
```json
{"type":"focus_lost","details":"Window lost focus for 3.2s"}
```

Screenshot metadata request:
```json
{"file_path":"attempts/<attempt_id>/2026-02-22T11-10-15Z.png"}
```

Standard error responses:
- 400 bad request/domain error
- 401 unauthorized
- 403 forbidden
- 404 not found
- 422 validation error
- 500 internal server error

WebSocket contract (planned):
- URL: `ws://<host>/ws/monitor`
- Auth: JWT (query/header transport to confirm)
- Event envelope:
```json
{"event":"attempt.updated","ts":"2026-02-22T11:12:00Z","payload":{}}
```
- Planned events:
  - `attempt.started`
  - `attempt.updated`
  - `attempt.submitted`
  - `violation.created`
  - `screenshot.captured`
  - `alert.raised`

## H) Client Apps Behavior

Admin portal (`admin/`):
- Current behavior in `admin/src/App.tsx`:
  - username/password login form
  - stores access token in `localStorage`
  - fetches `/auth/me` after login
  - shows logged-in identity
  - triggers `/admin/ping` check
- API client in `admin/src/lib/api.ts`:
  - `setToken/getToken/clearToken`
  - `authFetch` to attach auth header

Planned admin pages/routes:
- `/login`
- `/dashboard`
- `/exams` (will consume implemented backend FR-07 endpoints)
- `/monitor/:attemptId`
- `/reports`
- To confirm: final route names and component organization.

Student client (`client/`, planned):
- Planned screens:
  - login
  - exam start
  - active attempt
  - submit confirmation
- Planned services:
  - `LockdownManager`
  - `ScreenshotService`
  - `ViolationService`
  - `OfflineQueue`
- Service lifecycle:
  - start when attempt starts
  - stop on submission/termination

## I) Environment & Configuration

Server env vars (`server/.env`, `server/app/core/config.py`):
- `APP_NAME`
- `ENV`
- `HOST`
- `PORT`
- `LOG_LEVEL`
- `DATABASE_URL`
- `DATABASE_URL_TEST` (optional)
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_EXPIRES_MINUTES`

Safe example:
```env
APP_NAME=ExamShield
ENV=dev
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
DATABASE_URL=postgresql+psycopg://examshield:examshield@localhost:5432/examshield
DATABASE_URL_TEST=postgresql+psycopg://examshield:examshield@localhost:5432/examshield_test
JWT_SECRET_KEY=replace-with-strong-secret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=60
```

Admin env vars (`admin/.env`):
- `VITE_API_BASE_URL`

Example:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Dev vs prod:
- Dev: local Postgres via `server/docker-compose.yml`, localhost CORS.
- Prod: managed DB, strict CORS, HTTPS, strong key management and rotation.

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

Tests:
```bash
cd server
pytest
```

Notes:
- Auth tests require PostgreSQL reachable and migration applied.
- Milestone 2 tests:
  - `tests/test_exams_crud.py` covers admin exam CRUD, student 403, and exam 404 behavior.
  - `tests/test_questions_crud.py` covers admin question CRUD, student 403, and exam/question 404 behavior.

Coding conventions:
- Python:
  - format with `black`
  - lint with `ruff`
  - naming: snake_case modules/functions, PascalCase classes
  - layering: routers call services; services interact with models/db
- TypeScript/React:
  - API logic in `admin/src/lib/api.ts`
  - components/pages split as app grows
  - naming: PascalCase for components, camelCase for functions
- Folder rule for new backend module:
  - `server/app/api/routers/<module>.py`
  - `server/app/schemas/<module>.py`
  - `server/app/services/<module>_service.py`
  - corresponding tests in `server/tests/`

Git workflow:
- `main`: stable branch
- `dev`: integration branch
- `feature/<name>` from `dev`
- merge flow: feature -> dev -> main milestone release
- To confirm: minimum PR approvals and branch protection policy.

## K) "How to Reference This Doc" Section

Instruction template:

> When implementing new tasks, do not scan the repository. Use `docs/PROJECT_DOCUMENTATION.md` as the source of truth and only open files that need changes.
