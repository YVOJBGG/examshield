# ExamShield

ExamShield is organized as a monorepo with separate backend, admin UI, client app, and documentation.

## Repository Structure

- `server/`: FastAPI backend and automated tests.
- `admin/`: React + Vite admin dashboard.
- `client/`: Client application workspace.
- `docs/`: Project documents, diagrams, and specifications.

## Prerequisites

- Python `3.11+`
- Node.js `18+` (npm included)

## Setup

### 1) Server Setup (FastAPI)

From the repository root:

```bash
cd server
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create local environment variables file:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

### 2) Admin Setup (React + Vite)

From the repository root:

```bash
cd admin
npm install
npm run dev
```

## Testing

Run backend tests with `pytest`:

```bash
cd server
pytest
```

## Formatting

Use `ruff` for linting/quick fixes and `black` for formatting (in `server/`):

```bash
cd server
ruff check .
ruff check . --fix
black .
```
