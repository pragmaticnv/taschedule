"""
Domain models and validation for TICKLINE Task Scheduler.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import math


PRIORITY_LABELS: Dict[int, str] = {
    1: "Low",
    2: "Normal",
    3: "Medium",
    4: "High",
    5: "Critical",
}


@dataclass
class Task:
    task_id: str
    title: str
    notes: str = ""
    deadline: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_minutes: int = 30
    priority: int = 3  # 1 to 5
    status: str = "active"  # "active" or "completed"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    version: int = 1

    def __post_init__(self):
        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be blank or whitespace.")
        self.title = self.title.strip()

        # Validate estimated_minutes
        if self.estimated_minutes <= 0:
            raise ValueError("Estimated duration must be greater than zero minutes.")

        # Validate priority
        if not (1 <= self.priority <= 5):
            raise ValueError("Priority must be an integer between 1 (Low) and 5 (Critical).")

        # Validate status
        if self.status not in ("active", "completed"):
            raise ValueError(f"Invalid status '{self.status}'. Must be 'active' or 'completed'.")

        # Normalize timezone to UTC if naive
        if self.deadline.tzinfo is None:
            self.deadline = self.deadline.replace(tzinfo=timezone.utc)
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
        if self.completed_at and self.completed_at.tzinfo is None:
            self.completed_at = self.completed_at.replace(tzinfo=timezone.utc)

    @property
    def priority_label(self) -> str:
        return PRIORITY_LABELS.get(self.priority, f"P{self.priority}")

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        if self.status == "completed":
            return False
        ref = now or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        return self.deadline < ref

    def is_due_soon(self, now: Optional[datetime] = None, hours: int = 24) -> bool:
        if self.status == "completed":
            return False
        ref = now or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        diff_seconds = (self.deadline - ref).total_seconds()
        return 0 <= diff_seconds <= (hours * 3600)

    def is_upcoming(self, now: Optional[datetime] = None, hours: int = 24) -> bool:
        if self.status == "completed":
            return False
        ref = now or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        diff_seconds = (self.deadline - ref).total_seconds()
        return diff_seconds > (hours * 3600)

    def urgency_category(self, now: Optional[datetime] = None) -> str:
        if self.status == "completed":
            return "completed"
        if self.is_overdue(now):
            return "overdue"
        if self.is_due_soon(now):
            return "due_soon"
        return "upcoming"

    def time_remaining_str(self, now: Optional[datetime] = None) -> str:
        if self.status == "completed":
            return "Completed"
        ref = now or datetime.now(timezone.utc)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        diff = self.deadline - ref
        total_seconds = int(diff.total_seconds())

        is_past = total_seconds < 0
        secs = abs(total_seconds)

        days = secs // 86400
        hours = (secs % 86400) // 3600
        minutes = (secs % 3600) // 60

        if days > 0:
            time_str = f"{days}d {hours}h"
        elif hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"

        if is_past:
            return f"{time_str} overdue"
        return f"{time_str} left"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "notes": self.notes,
            "deadline": self.deadline.isoformat(),
            "estimated_minutes": self.estimated_minutes,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            notes=data.get("notes", ""),
            deadline=datetime.fromisoformat(data["deadline"]),
            estimated_minutes=int(data["estimated_minutes"]),
            priority=int(data["priority"]),
            status=data.get("status", "active"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            version=int(data.get("version", 1)),
        )

