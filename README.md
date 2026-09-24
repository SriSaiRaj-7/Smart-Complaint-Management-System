# Smart Complaint Management System

A console-based Data Structures mini-project for managing college hostel complaints. It uses only Python's standard library and persists data in SQLite.

## Run

Use Python 3.10 or newer:

```powershell
python main.py
```

The application creates `complaints.db` in the project folder on first run. The database file is intentionally not required in source control; it is generated at runtime.

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

Category weights are electrical=5, plumbing=4, hostel=3, academic=2, and other=1. Lower scores are dispatched first. Complaints older than 24 simulated hours escalate one level at a time. Use menu option 5 to advance the simulated clock and run a check.

The service rejects a duplicate title from the same resident when it was submitted within the previous ten minutes. Invalid menu values and empty required fields are handled interactively.

## Project layout

- `models.py`: typed `Complaint` and `StatusChange` data classes.
- `db.py`: SQLite schema and persistence operations.
- `services/complaint_service.py`: heap, deque, hash-map indexes, escalation, statistics, and audit-stack logic.
- `main.py`: terminal input/output and menu wiring.