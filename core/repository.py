"""
SQLite Persistence Layer for TICKLINE Task Scheduler.
Handles atomic CRUD, settings persistence, and realistic academic seed data.
"""
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from core.models import Task


DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tickline.db")


class TaskRepository:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        # For in-memory databases, keep a persistent connection so tables aren't wiped across calls
        self._is_memory = (db_path == ":memory:")
        self._memory_conn: Optional[sqlite3.Connection] = None
        if not self._is_memory:
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        else:
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._is_memory and self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    notes TEXT,
                    deadline TEXT NOT NULL,
                    estimated_minutes INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_task(self, task: Task) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, title, notes, deadline, estimated_minutes, priority,
                    status, created_at, updated_at, completed_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.title,
                task.notes,
                task.deadline.isoformat(),
                task.estimated_minutes,
                task.priority,
                task.status,
                task.created_at.isoformat(),
                task.updated_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else None,
                task.version
            ))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task(row)

    def get_all_tasks(self) -> List[Task]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY created_at ASC")
            rows = cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    def get_active_tasks(self) -> List[Task]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE status = 'active' ORDER BY deadline ASC")
            rows = cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    def get_completed_tasks(self) -> List[Task]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE status = 'completed' ORDER BY completed_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_task(r) for r in rows]

    def update_task(self, task: Task) -> bool:
        task.updated_at = datetime.now(timezone.utc)
        task.version += 1
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET
                    title = ?,
                    notes = ?,
                    deadline = ?,
                    estimated_minutes = ?,
                    priority = ?,
                    status = ?,
                    updated_at = ?,
                    completed_at = ?,
                    version = ?
                WHERE task_id = ?
            """, (
                task.title,
                task.notes,
                task.deadline.isoformat(),
                task.estimated_minutes,
                task.priority,
                task.status,
                task.updated_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else None,
                task.version,
                task.task_id
            ))
            conn.commit()
            return cursor.rowcount > 0

    def delete_task(self, task_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def complete_task(self, task_id: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        task.status = "completed"
        now = datetime.now(timezone.utc)
        task.completed_at = now
        task.updated_at = now
        task.version += 1
        self.update_task(task)
        return task

    def reopen_task(self, task_id: str) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        task.status = "active"
        task.completed_at = None
        task.updated_at = datetime.now(timezone.utc)
        task.version += 1
        self.update_task(task)
        return task

    def get_setting(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def set_setting(self, key: str, value: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def reset_all(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks")
            cursor.execute("DELETE FROM settings")
            conn.commit()

    def seed_demo_data(self, force: bool = False) -> int:
        """
        Seeds deterministic, realistic academic tasks for coursework demonstration.
        """
        if not force and len(self.get_all_tasks()) > 0:
            return 0

        self.reset_all()

        now = datetime.now(timezone.utc)

        demo_tasks = [
            Task(
                task_id="TSK-101",
                title="OS Lab 3: Multithreaded Semaphore Buffer",
                notes="Submit synchronized consumer-producer C implementation with thread safety locks.",
                deadline=now - timedelta(hours=3),  # Overdue
                estimated_minutes=45,
                priority=5,  # Critical
                status="active",
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2),
            ),
            Task(
                task_id="TSK-102",
                title="ADSA Assignment 4: Red-Black Tree Rotation Analysis",
                notes="Derive asymptotic bounds for recoloring steps and write pseudocode for case 3 rotation.",
                deadline=now + timedelta(hours=2),  # Due very soon
                estimated_minutes=60,
                priority=4,  # High
                status="active",
                created_at=now - timedelta(days=1, hours=5),
                updated_at=now - timedelta(days=1, hours=5),
            ),
            Task(
                task_id="TSK-103",
                title="Computer Networks: WireShark Packet Inspection Report",
                notes="Trace TCP 3-way handshake and analyze window scaling in lab trace dump.",
                deadline=now + timedelta(hours=5),  # Due today
                estimated_minutes=30,
                priority=3,  # Medium
                status="active",
                created_at=now - timedelta(days=1, hours=2),
                updated_at=now - timedelta(days=1, hours=2),
            ),
            Task(
                task_id="TSK-104",
                title="ADSA Project 17: Viva & Demonstration Prep",
                notes="Prepare slide deck and practice live Heap Laboratory trace explanation for examiner.",
                deadline=now + timedelta(hours=14),  # Due tonight / tomorrow morning
                estimated_minutes=40,
                priority=5,  # Critical
                status="active",
                created_at=now - timedelta(hours=18),
                updated_at=now - timedelta(hours=18),
            ),
            Task(
                task_id="TSK-105",
                title="Database Systems: B+ Tree Indexing Homework",
                notes="Calculate splitting frequency on 10,000 synthetic random records with page size 4KB.",
                deadline=now + timedelta(days=2),  # Upcoming
                estimated_minutes=90,
                priority=2,  # Normal
                status="active",
                created_at=now - timedelta(hours=10),
                updated_at=now - timedelta(hours=10),
            ),
            Task(
                task_id="TSK-106",
                title="Discrete Mathematics: Graph Coloring Quiz Study",
                notes="Review planar graph 4-color theorem proofs and chromatic polynomial calculation.",
                deadline=now + timedelta(days=4),  # Upcoming
                estimated_minutes=75,
                priority=3,  # Medium
                status="active",
                created_at=now - timedelta(hours=6),
                updated_at=now - timedelta(hours=6),
            ),
            Task(
                task_id="TSK-100",
                title="Software Engineering: Sprint 2 Retrospective Notes",
                notes="Document velocity deviations and post-mortem on merge conflict resolution.",
                deadline=now - timedelta(days=1),
                estimated_minutes=25,
                priority=2,
                status="completed",
                created_at=now - timedelta(days=4),
                updated_at=now - timedelta(hours=20),
                completed_at=now - timedelta(hours=20),
            ),
        ]

        for t in demo_tasks:
            self.add_task(t)

        self.set_setting("ordering_policy", "earliest_deadline")
        self.set_setting("capacity_work_window_minutes", "180")
        return len(demo_tasks)

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            task_id=row["task_id"],
            title=row["title"],
            notes=row["notes"] or "",
            deadline=datetime.fromisoformat(row["deadline"]),
            estimated_minutes=row["estimated_minutes"],
            priority=row["priority"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            version=row["version"],
        )
