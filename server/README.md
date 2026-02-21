# ExamShield Server

## Prerequisites

- Python 3.11+

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

## Run

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
