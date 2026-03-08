# ExamShield Student Client (Milestone 3)

Minimal PyQt student app for:
- login
- loading assigned exam
- starting attempt
- answering questions
- autosave
- submit
- local disk caching for offline-safe answer persistence

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

## Local Answer Cache Behavior

- The client stores answers as JSON under:
  - `client/app_data/cache/attempt_<attempt_id>.json`
  - `client/app_data/cache/exam_<exam_id>.json`
- Each answer edit is written to local cache immediately.
- If autosave fails, cache stays `dirty` and answers remain local.
- Retry points:
  - periodic autosave timer
  - manual `Autosave Now`
  - automatic sync attempt when exam window opens with dirty cache
- On successful submit, attempt cache is archived to `client/app_data/archive/`.
- Corrupted cache files are renamed with `.corrupt.<timestamp>` and ignored safely.

## Manual Verification (Offline/Reconnect)

1. Start backend server and run client.
2. Login with student credentials and open an exam.
3. Type answers and confirm status shows `Saved locally`.
4. Stop backend (or disconnect network).
5. Trigger `Autosave Now` and confirm status shows `Autosave failed, changes kept locally`.
6. Close and reopen client, login again to same exam/attempt; confirm previous answers are preloaded.
7. Restore backend connectivity.
8. Wait for periodic autosave or click `Autosave Now`; confirm status becomes `Synced to server`.
9. Submit exam; confirm cache file moves to archive and editing is disabled.
