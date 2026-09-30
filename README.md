# Smart Complaint Management System

A Flask-based Data Structures mini-project for managing college hostel complaints. It persists complaints and audit history in SQLite while reusing the existing service's heap, queues, hash-map indexes, escalation, and audit-stack logic.

## Run

Use Python 3.10 or newer. Install dependencies and start the development server:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:5000`. The application creates `complaints.db` in the project folder on first run. Set `FLASK_SECRET_KEY` in the environment when using the app beyond local development.

## Web routes

- `/`: priority-ordered complaint dashboard and resolve-next action.
- `/raise`: create a complaint.
- `/search`: look up complaints by ID or category.
- `/escalation`: view escalation targets, advance simulated time, and check overdue complaints.
- `/audit/<complaint_id>`: view the newest-first status history.
- `/stats`: view complaint counts and average resolution time.

## DSA mapping

| Feature | Data structure / concept | Why it is used |
| --- | --- | --- |
| Dispatch by priority | `heapq` min-heap | Retrieves the lowest priority score efficiently. |
| Same-priority dispatch | `collections.deque` | Preserves FIFO order among equal-score complaints. |
| ID and category search | Python `dict` and sets | Provides average O(1) index lookup. |
| Escalation | Escalation chain | Moves overdue complaints from warden to dean to principal. |
| Audit trail | Per-complaint list used as a stack | The newest status change is available first. |
| Persistence | SQLite via `sqlite3` | Keeps complaints and audit entries across runs. |

## Priority and escalation

The score is recalculated as:

`urgency * 2 + category_weight + hours_since_raised / 24`

Category weights are electrical=5, plumbing=4, hostel=3, academic=2, and other=1. Lower scores are dispatched first. Complaints older than 24 simulated hours escalate one level at a time. Use the escalation page to advance the simulated clock and run a check.

The service rejects a duplicate title from the same resident when it was submitted within the previous ten minutes. Invalid form input and duplicate submissions are reported with flash messages.

## Project layout

- `models.py`: typed `Complaint` and `StatusChange` data classes.
- `db.py`: SQLite schema and persistence operations.
- `services/complaint_service.py`: heap, deque, hash-map indexes, escalation, statistics, and audit-stack logic.
- `main.py`: Flask routes and request-scoped service lifecycle.