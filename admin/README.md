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
