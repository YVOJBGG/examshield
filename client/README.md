# ExamShield Student Client (Milestone 5)

Minimal PyQt student app for:
- login
- loading assigned exam
- starting attempt
- answering questions
- autosave
- submit
- local disk caching for offline-safe answer persistence
- live monitoring status events for admin dashboard
- best-effort client-side violation reporting

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

## Test

```powershell
cd client
.venv\Scripts\Activate.ps1
pytest
```

## Notes

- Use a seeded student account from server seed data (for example `student1` / `student123`).
- Enter a valid exam UUID in the login screen.
- Autosave runs every 25 seconds and can be triggered manually.
- Monitoring starts automatically after attempt start and sends periodic heartbeat updates.
- Violation reporting is best-effort and must not block the exam flow.

## Milestone 5 Violation Reporting

The student client now sends violation events to backend endpoint:
- `POST /violations` (student JWT required)

Currently implemented UI triggers:
- `focus_lost`: sent when the exam window is deactivated or loses focus while the attempt is active
- `manual_flag`: sent from a dev-only `Trigger Test Violation` control

Behavior notes:
- violations are tied to the current `attempt_id`
- repeated `focus_lost` reports are throttled with a 5-second cooldown
- reporting failures do not crash the exam flow
- a small status line in the exam window shows the last violation send result
- full lockdown and advanced OS-level monitoring are intentionally deferred to a later milestone

Dev-mode toggle:

```powershell
$env:EXAMSHIELD_DEV_MODE="1"
```

## Milestone 4 Live Monitoring (Student -> Server)

The student client now sends monitoring events to backend endpoint:
- `POST /monitoring/status` (student JWT required)

This uses the existing `requests`-based REST client (no new dependency added).

Event triggers in the current UI flow:
- `connected`: right after login + exam load + attempt start in login flow.
- `in_exam`: when exam window opens.
- `autosave`: after successful answer autosave.
- `submitted`: after successful final submit.
- `disconnected`: best-effort when exam window closes before submit.
- heartbeat: every 12 seconds during active exam, sent as `in_exam`.

If monitoring send fails, exam actions continue. The exam window shows:
- `Live monitoring connected`
- `Live monitoring unavailable`

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

## Automated tests

- `tests/test_auth_manager.py` validates login/logout token state handling.
- `tests/test_network_client.py` validates HTTP, network, multipart upload, and invalid JSON handling.
- `tests/test_local_cache.py` validates cache persistence, corruption recovery, and archive behavior.
- `tests/test_quiz_manager.py` covers load/start/autosave/submit flows, offline dirty-cache behavior, cache restore, and MCQ cache normalization.
- `tests/test_monitoring_client.py` covers monitoring session state and event sending.
- `tests/test_violation_service.py` covers success, failure, and cooldown behavior for violations.
- `tests/test_shortcut_detection_service.py` covers shortcut de-duplication and release-reset regression behavior.
