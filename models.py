"""Typed data models for the hostel complaint system."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Category = Literal["electrical", "plumbing", "academic", "hostel", "other"]
Status = Literal["open", "in_progress", "escalated", "resolved"]


@dataclass(slots=True)
class Complaint:
    """A complaint and the fields needed to route it through the system."""

    id: int | None
    title: str
    description: str
    category: Category
    raised_by: str
    urgency: int
    priority_score: float
    status: Status
    timestamp: datetime
    escalation_level: int = 0


@dataclass(frozen=True, slots=True)
class StatusChange:
    """One entry in a complaint's status-change audit trail."""

    complaint_id: int
    old_status: Status
    new_status: Status
    changed_at: datetime
    note: str = ""
