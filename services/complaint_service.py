"""Business rules and explicit data structures for complaint processing."""

from __future__ import annotations

import heapq
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Callable

from db import ComplaintDatabase
from models import Category, Complaint, Status, StatusChange

CATEGORY_WEIGHTS: dict[Category, int] = {
    "electrical": 5,
    "plumbing": 4,
    "academic": 2,
    "hostel": 3,
    "other": 1,
}
ESCALATION_AFTER_HOURS = 24
MAX_ESCALATION_LEVEL = 2


class ComplaintService:
    """Coordinate complaint operations using in-memory DSA structures.

    The dictionaries provide average O(1) lookup by id and category. The heap
    gives the smallest priority score first, while a deque per score preserves
    FIFO order among complaints that have the same priority. Audit histories
    are lists used as stacks: the newest status change is viewed first.
    """

    def __init__(
        self,
        database: ComplaintDatabase,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.database = database
        self.clock = clock or datetime.now
        self.time_offset = timedelta(0)
        self.by_id: dict[int, Complaint] = {}
        self.by_category: dict[Category, set[int]] = defaultdict(set)
        self.dispatch_heap: list[float] = []
        self.same_priority_queues: dict[float, deque[int]] = {}
        self.audit_stacks: dict[int, list[StatusChange]] = {}
        self._load_indexes()

    def _load_indexes(self) -> None:
        for complaint in self.database.get_all_complaints():
            if complaint.id is None:
                continue
            self.by_id[complaint.id] = complaint
            self.by_category[complaint.category].add(complaint.id)
            self.audit_stacks[complaint.id] = self.database.get_status_history(complaint.id)
        self.rebuild_dispatch_queue()

    def now(self) -> datetime:
        return self.clock() + self.time_offset

    @staticmethod
    def calculate_priority(
        urgency: int,
        category: Category,
        raised_at: datetime,
        current_time: datetime,
    ) -> float:
        """Calculate urgency, category, and age as one dispatch score."""
        hours_since_raised = max(
            0.0, (current_time - raised_at).total_seconds() / 3600
        )
        return round(urgency * 2 + CATEGORY_WEIGHTS[category] + hours_since_raised / 24, 4)

    def is_duplicate(self, title: str, raised_by: str, window_minutes: int = 10) -> bool:
        """Avoid accidental repeated submissions in a short time window."""
        cutoff = self.now() - timedelta(minutes=window_minutes)
        normalized_title = title.strip().casefold()
        normalized_user = raised_by.strip().casefold()
        return any(
            complaint.title.casefold() == normalized_title
            and complaint.raised_by.casefold() == normalized_user
            and complaint.timestamp >= cutoff
            for complaint in self.by_id.values()
        )

    def raise_complaint(
        self,
        title: str,
        description: str,
        category: Category,
        raised_by: str,
        urgency: int,
    ) -> Complaint:
        if not title.strip() or not description.strip() or not raised_by.strip():
            raise ValueError("Title, description, and resident name are required")
        if urgency not in range(1, 6):
            raise ValueError("Urgency must be between 1 and 5")
        if self.is_duplicate(title, raised_by):
            raise ValueError("A similar complaint was raised by this user recently")

        timestamp = self.now()
        complaint = Complaint(
            id=None,
            title=title.strip(),
            description=description.strip(),
            category=category,
            raised_by=raised_by.strip(),
            urgency=urgency,
            priority_score=self.calculate_priority(
                urgency, category, timestamp, timestamp
            ),
            status="open",
            timestamp=timestamp,
        )
        self.database.add_complaint(complaint)
        if complaint.id is None:
            raise RuntimeError("Database did not assign a complaint id")
        self.by_id[complaint.id] = complaint
        self.by_category[category].add(complaint.id)
        self.audit_stacks[complaint.id] = []
        self._record_status_change(complaint, "open", "Complaint raised")
        self.rebuild_dispatch_queue()
        return complaint

    def rebuild_dispatch_queue(self) -> None:
        """Rebuild dispatch indexes after time or complaint status changes."""
        self.dispatch_heap = []
        self.same_priority_queues = {}
        grouped: dict[float, deque[int]] = defaultdict(deque)
        for complaint in sorted(self.by_id.values(), key=lambda item: item.timestamp):
            if complaint.status == "resolved" or complaint.id is None:
                continue
            complaint.priority_score = self.calculate_priority(
                complaint.urgency,
                complaint.category,
                complaint.timestamp,
                self.now(),
            )
            grouped[complaint.priority_score].append(complaint.id)
        for score, complaint_ids in grouped.items():
            self.same_priority_queues[score] = complaint_ids
            heapq.heappush(self.dispatch_heap, score)

    def resolve_next(self) -> Complaint | None:
        """Pop the next complaint from the heap and its FIFO tie queue."""
        while self.dispatch_heap:
            score = heapq.heappop(self.dispatch_heap)
            queue = self.same_priority_queues.get(score)
            if not queue:
                continue
            complaint_id = queue.popleft()
            if queue:
                heapq.heappush(self.dispatch_heap, score)
            complaint = self.by_id[complaint_id]
            if complaint.status == "resolved":
                continue
            self._record_status_change(complaint, "resolved", "Resolved by dispatcher")
            self.database.update_complaint(complaint)
            return complaint
        return None

    def search_by_id(self, complaint_id: int) -> Complaint | None:
        return self.by_id.get(complaint_id)

    def search_by_category(self, category: Category) -> list[Complaint]:
        return [self.by_id[item] for item in sorted(self.by_category[category])]

    def all_by_priority(self) -> list[Complaint]:
        self.rebuild_dispatch_queue()
        ordered: list[Complaint] = []
        for score in sorted(self.same_priority_queues):
            ordered.extend(
                self.by_id[complaint_id]
                for complaint_id in self.same_priority_queues[score]
            )
        return ordered

    def advance_time(self, hours: float) -> None:
        if hours < 0:
            raise ValueError("Time advance cannot be negative")
        self.time_offset += timedelta(hours=hours)
        self.rebuild_dispatch_queue()

    def force_escalation_check(self) -> list[Complaint]:
        """Move overdue open complaints through warden, dean, principal."""
        escalated: list[Complaint] = []
        for complaint in self.by_id.values():
            age_hours = (self.now() - complaint.timestamp).total_seconds() / 3600
            if complaint.status == "resolved" or age_hours < ESCALATION_AFTER_HOURS:
                continue
            if complaint.escalation_level < MAX_ESCALATION_LEVEL:
                complaint.escalation_level += 1
                self._record_status_change(
                    complaint,
                    "escalated",
                    f"Escalated to {self.escalation_target(complaint.escalation_level)}",
                )
                self.database.update_complaint(complaint)
                escalated.append(complaint)
        self.rebuild_dispatch_queue()
        return escalated

    @staticmethod
    def escalation_target(level: int) -> str:
        return ("warden", "dean", "principal")[min(level, MAX_ESCALATION_LEVEL)]

    def audit_trail(self, complaint_id: int) -> list[StatusChange]:
        """Return the stack newest-first for an audit-trail view."""
        return list(reversed(self.audit_stacks.get(complaint_id, [])))

    def stats(self) -> dict[str, object]:
        category_counts: dict[str, int] = defaultdict(int)
        status_counts: dict[str, int] = defaultdict(int)
        resolution_hours: list[float] = []
        for complaint in self.by_id.values():
            category_counts[complaint.category] += 1
            status_counts[complaint.status] += 1
            resolved_at = next(
                (
                    change.changed_at
                    for change in self.audit_stacks.get(complaint.id or 0, [])
                    if change.new_status == "resolved"
                ),
                None,
            )
            if resolved_at:
                resolution_hours.append(
                    (resolved_at - complaint.timestamp).total_seconds() / 3600
                )
        average = sum(resolution_hours) / len(resolution_hours) if resolution_hours else 0.0
        return {
            "by_category": dict(category_counts),
            "by_status": dict(status_counts),
            "average_resolution_hours": average,
        }

    def _record_status_change(
        self, complaint: Complaint, new_status: Status, note: str
    ) -> None:
        if complaint.id is None:
            raise ValueError("Complaint must have an id before recording history")
        old_status = complaint.status
        complaint.status = new_status
        change = StatusChange(
            complaint_id=complaint.id,
            old_status=old_status,
            new_status=new_status,
            changed_at=self.now(),
            note=note,
        )
        self.audit_stacks[complaint.id].append(change)
        self.database.add_status_change(change)
