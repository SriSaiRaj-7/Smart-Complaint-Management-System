"""SQLite persistence for complaints and their audit history."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from models import Complaint, StatusChange


class ComplaintDatabase:
    """Persist domain data without leaking SQL concerns into service logic."""

    def __init__(self, database_path: str = "complaints.db") -> None:
        self.database_path = Path(database_path)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                raised_by TEXT NOT NULL,
                urgency INTEGER NOT NULL,
                priority_score REAL NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                escalation_level INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id INTEGER NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (complaint_id) REFERENCES complaints(id)
            );
            """
        )
        self.connection.commit()

    def add_complaint(self, complaint: Complaint) -> Complaint:
        cursor = self.connection.execute(
            """
            INSERT INTO complaints
                 (title, description, category, raised_by, urgency, priority_score,
                  status, timestamp, escalation_level)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                complaint.title,
                complaint.description,
                complaint.category,
                complaint.raised_by,
                complaint.urgency,
                complaint.priority_score,
                complaint.status,
                complaint.timestamp.isoformat(),
                complaint.escalation_level,
            ),
        )
        self.connection.commit()
        complaint.id = int(cursor.lastrowid)
        return complaint

    def get_complaint(self, complaint_id: int) -> Complaint | None:
        row = self.connection.execute(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id,)
        ).fetchone()
        return self._row_to_complaint(row) if row else None

    def get_all_complaints(self) -> list[Complaint]:
        rows = self.connection.execute(
            "SELECT * FROM complaints ORDER BY id"
        ).fetchall()
        return [self._row_to_complaint(row) for row in rows]

    def update_complaint(self, complaint: Complaint) -> None:
        if complaint.id is None:
            raise ValueError("Cannot update a complaint without an id")
        self.connection.execute(
            """
            UPDATE complaints
            SET priority_score = ?, status = ?, escalation_level = ?
            WHERE id = ?
            """,
            (
                complaint.priority_score,
                complaint.status,
                complaint.escalation_level,
                complaint.id,
            ),
        )
        self.connection.commit()

    def add_status_change(self, change: StatusChange) -> None:
        self.connection.execute(
            """
            INSERT INTO status_history
                (complaint_id, old_status, new_status, changed_at, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                change.complaint_id,
                change.old_status,
                change.new_status,
                change.changed_at.isoformat(),
                change.note,
            ),
        )
        self.connection.commit()

    def get_status_history(self, complaint_id: int) -> list[StatusChange]:
        rows = self.connection.execute(
            """
            SELECT complaint_id, old_status, new_status, changed_at, note
            FROM status_history
            WHERE complaint_id = ?
            ORDER BY id
            """,
            (complaint_id,),
        ).fetchall()
        return [
            StatusChange(
                complaint_id=int(row["complaint_id"]),
                old_status=row["old_status"],
                new_status=row["new_status"],
                changed_at=datetime.fromisoformat(row["changed_at"]),
                note=row["note"],
            )
            for row in rows
        ]

    def close(self) -> None:
        self.connection.close()

    @staticmethod
    def _row_to_complaint(row: sqlite3.Row) -> Complaint:
        data: dict[str, Any] = dict(row)
        return Complaint(
            id=int(data["id"]),
            title=data["title"],
            description=data["description"],
            category=data["category"],
            raised_by=data["raised_by"],
            urgency=int(data["urgency"]),
            priority_score=float(data["priority_score"]),
            status=data["status"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            escalation_level=int(data["escalation_level"]),
        )
