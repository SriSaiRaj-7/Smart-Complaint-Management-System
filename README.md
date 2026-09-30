# Smart Complaint Management System

A Tkinter desktop Data Structures mini-project for managing college complaints. It persists complaints and audit history in SQLite while reusing the existing service's heap, queues, hash-map indexes, escalation, and audit-stack logic.

## Run

Use Python 3.10 or newer with Tkinter available (included with most standard Python installations). No third-party packages are required.

```powershell
python main.py
```

The application creates `complaints.db` in the project folder on first run. Close the window to close the database connection cleanly.

## Desktop actions

- Raise Complaint: submit a complaint with its category and urgency.
- View All: display complaints in priority order.
- Resolve Next: resolve the next complaint from the dispatch heap.
- Search: look up a complaint by ID or category.
- Escalation: inspect escalation targets, advance simulated time, and check overdue complaints.
- Audit Trail: view a complaint's newest-first status history.
- Stats: view counts by category and status and average resolution time.

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

Category weights are electrical=5, plumbing=4, hostel=3, academic=2, and other=1. Lower scores are dispatched first. Complaints older than 24 simulated hours escalate one level at a time. Use the escalation window to advance simulated time and run a check.

The service rejects a duplicate title from the same resident when it was submitted within the previous ten minutes. Invalid form input and duplicate submissions are reported with flash messages.

## Project layout

- `models.py`: typed `Complaint` and `StatusChange` data classes.
- `db.py`: SQLite schema and persistence operations.
- `services/complaint_service.py`: heap, deque, hash-map indexes, escalation, statistics, and audit-stack logic.
- `main.py`: Tkinter interface and desktop event handlers.