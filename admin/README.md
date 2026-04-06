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

## End Exam and Analytics

- The exams list and exam editor now include admin actions for ending an exam and opening analytics.
- `End Exam` calls backend endpoint `POST /admin/exams/{exam_id}/end`.
- Before sending the request, the UI asks for confirmation because active student attempts will be force-submitted.
- While the request is running, the action button is disabled and shows a loading label.
- On success, the UI navigates to `/exams/{exam_id}/analytics` and shows a success banner.
- The analytics page loads backend data from `GET /admin/exams/{exam_id}/analytics` and summarizes:
  - attempt completion
  - force-submitted attempts
  - durations
  - violations and screenshots
  - question-level analytics and MCQ option distributions when available

## Manual test

1. Login as an admin user.
2. Open `/` and create or open an exam.
3. Click `End Exam` from the exams list or exam editor and confirm the warning dialog.
4. Verify the button shows a loading state and the app navigates to `/exams/:examId/analytics`.
5. Verify the analytics page shows the success banner and exam metrics from the backend.
6. Return to the exams list and confirm the exam now shows `Ended`.
7. Open `/monitoring`.
8. Start a student exam from the client.
9. Trigger focus loss or the client-side test violation.
10. Verify the admin UI shows:
   - a live toast
   - a highlighted attempt row
   - increased alert count and latest violation type
   - populated violations panel after clicking `View Violations`
