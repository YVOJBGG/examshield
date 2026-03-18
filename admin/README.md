# ExamShield Admin

## Setup

```bash
npm install
```

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Start development server:

```bash
npm run dev
```

## Milestone 4 Live Monitoring

- Login as an `admin` user first.
- Open the `Live Monitoring` page from the top navigation, or go to `/monitoring`.
- The page connects to backend WebSocket endpoint `/ws/admin/monitor?token=<JWT>` automatically.
- Dashboard rows update live from monitoring `snapshot` and `event` messages (no polling).
- The page shows connection state (`Connected`, `Connecting`, `Disconnected`) and last message timestamp.

## Milestone 5 Live Violations and Alerts

- The monitoring page now also handles WebSocket messages of type `violation`.
- When a violation arrives, the matching attempt row is updated immediately:
  - row is highlighted
  - alert count increases
  - latest violation type is shown
- A lightweight in-app toast appears for each new live violation, for example:
  - `Violation: student1 - focus_lost`
- Use the `Show only attempts with alerts` checkbox to filter the dashboard.
- Click `View Violations` on any attempt row to open the per-attempt violations panel.
- The panel loads backend data from `GET /violations/attempt/{attempt_id}` and shows loading and error states.

## Manual test

1. Login as an admin user.
2. Open `/monitoring`.
3. Start a student exam from the client.
4. Trigger focus loss or the client-side test violation.
5. Verify the admin UI shows:
   - a live toast
   - a highlighted attempt row
   - increased alert count and latest violation type
   - populated violations panel after clicking `View Violations`
