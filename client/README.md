# ExamShield Student Client (Milestone 3)

Minimal PyQt student app for:
- login
- loading assigned exam
- starting attempt
- answering questions
- autosave
- submit

## Requirements

- Python 3.11+
- Running backend server (`http://127.0.0.1:8000` by default)

## Install

```powershell
cd client
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configure API URL (optional)

Default API base URL is `http://127.0.0.1:8000`.

Set environment variable if needed:

```powershell
$env:EXAMSHIELD_API_BASE_URL="http://127.0.0.1:8000"
```

## Run

```powershell
cd client
.venv\Scripts\Activate.ps1
python -m app.main
```

## Notes

- Use a seeded student account from server seed data (for example `student1` / `student123`).
- Enter a valid exam UUID in the login screen.
- Autosave runs every 25 seconds and can be triggered manually.
