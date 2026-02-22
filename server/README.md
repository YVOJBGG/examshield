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

## Lint and Format

```bash
ruff check .
ruff check . --fix
black .
```
