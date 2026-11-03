"""
Scheduler and Policy Engine for TICKLINE.
Maintains the live Binary Min-Heap and produces deterministic recommendations.
"""
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta
from core.models import Task
from core.priority_queue import MinHeap, HeapTraceEvent
from core.repository import TaskRepository


class SchedulingPolicy(str, Enum):
    EARLIEST_DEADLINE = "earliest_deadline"
    PRIORITY_FIRST = "priority_first"


class Scheduler:
    """
    Coordinates task ordering policy, the underlying custom binary min-heap,
    and explanatory diagnostic analysis.
    """

    def __init__(self, repository: TaskRepository):
        self.repo = repository
        self.heap = MinHeap[Tuple[Any, ...], Task]()
        self._policy: SchedulingPolicy = SchedulingPolicy(
            self.repo.get_setting("ordering_policy", SchedulingPolicy.EARLIEST_DEADLINE.value)
        )
        self.rebuild_heap()

    @property
    def policy(self) -> SchedulingPolicy:
        return self._policy

    @policy.setter
    def policy(self, new_policy: SchedulingPolicy) -> None:
        self._policy = new_policy
        self.repo.set_setting("ordering_policy", new_policy.value)
        self.rebuild_heap()

    def generate_task_key(self, task: Task) -> Tuple[Any, ...]:
        """
        Creates a deterministic composite comparison tuple for the min-heap.
        
        EDF Policy:
          (1) deadline ascending (earliest first)
          (2) priority descending (-priority for min-heap)
          (3) created_at ascending (FIFO for tie)
          (4) task_id ascending (stable deterministic tie-breaker)
          
        Priority-First Policy:
          (1) priority descending (-priority for min-heap)
          (2) deadline ascending
          (3) created_at ascending
          (4) task_id ascending
        """
        deadline_str = task.deadline.isoformat()
        priority_inverted = -task.priority
        created_str = task.created_at.isoformat()
        stable_id = task.task_id

        if self._policy == SchedulingPolicy.EARLIEST_DEADLINE:
            return (deadline_str, priority_inverted, created_str, stable_id)
        else:
            return (priority_inverted, deadline_str, created_str, stable_id)

    def rebuild_heap(self) -> None:
        """
        Reconstructs the min-heap from active tasks in SQLite using bottom-up heapify in O(n).
        Ensures perfect consistency without stale pointers.
        """
        active_tasks = self.repo.get_active_tasks()
        items = [(self.generate_task_key(t), t) for t in active_tasks]
        self.heap.build_heap(items, explanation_label=f"Rebuild from repository ({self._policy.value})")

    def peek_next(self) -> Optional[Task]:
        """
        Inspect the highest-priority active task at the root of the min-heap.
        Time Complexity: O(1)
        """
        return self.heap.peek()

    def get_ranked_queue(self) -> List[Task]:
        """
        Returns active tasks in exact scheduler order via sorted projection.
        Time Complexity: O(n log n)
        """
        return self.heap.get_sorted_projection()

    def complete_next_task(self) -> Tuple[Optional[Task], Optional[Task]]:
        """
        Completes the current top task from the heap.
        Returns (completed_task, new_next_task).
        Time Complexity: O(log n) pop + SQLite update
        """
        top_task = self.heap.pop()
        if not top_task:
            return None, None

        completed = self.repo.complete_task(top_task.task_id)
        new_next = self.heap.peek()
        return completed, new_next

    def explain_recommendation(self, task: Optional[Task] = None) -> Dict[str, Any]:
        """
        Generates a transparent, algorithmic breakdown explaining why the top task
        ranks first in the active min-heap.
        """
        if task is None:
            task = self.peek_next()

        if task is None:
            return {
                "has_task": False,
                "message": "Queue is currently empty. No active tasks to schedule.",
                "policy_name": self._policy.name.replace("_", " ").title(),
                "criteria": []
            }

        queue = self.get_ranked_queue()
        runner_up = queue[1] if len(queue) > 1 else None
        now = datetime.now(timezone.utc)

        criteria = []

        if self._policy == SchedulingPolicy.EARLIEST_DEADLINE:
            primary_reason = f"Earliest active deadline: {task.deadline.strftime('%b %d, %Y at %H:%M UTC')} ({task.time_remaining_str(now)})"
            if runner_up:
                if task.deadline < runner_up.deadline:
                    criteria.append({
                        "rule": "Primary: Earliest Deadline",
                        "status": "Decisive",
                        "details": f"Deadline is {runner_up.deadline - task.deadline} earlier than runner-up '{runner_up.title}'."
                    })
                elif task.deadline == runner_up.deadline:
                    criteria.append({
                        "rule": "Primary: Earliest Deadline",
                        "status": "Tied",
                        "details": f"Equal deadline with runner-up '{runner_up.title}' ({task.deadline.strftime('%H:%M')}). Resolving by priority."
                    })
                    if task.priority > runner_up.priority:
                        criteria.append({
                            "rule": "Tie-Breaker 1: Priority Descending",
                            "status": "Decisive",
                            "details": f"Priority {task.priority_label} ({task.priority}) exceeds runner-up ({runner_up.priority})."
                        })
                    elif task.priority == runner_up.priority:
                        criteria.append({
                            "rule": "Tie-Breaker 1: Priority Descending",
                            "status": "Tied",
                            "details": f"Equal priority ({task.priority}). Resolving by creation timestamp."
                        })
                        if task.created_at <= runner_up.created_at:
                            criteria.append({
                                "rule": "Tie-Breaker 2: Creation Timestamp (FIFO)",
                                "status": "Decisive",
                                "details": f"Created earlier at {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}."
                            })
            else:
                criteria.append({
                    "rule": "Primary: Earliest Deadline",
                    "status": "Decisive",
                    "details": "Single active task in the priority queue."
                })
        else:
            # PRIORITY_FIRST
            primary_reason = f"Highest priority ranking: {task.priority_label} (Level {task.priority})"
            if runner_up:
                if task.priority > runner_up.priority:
                    criteria.append({
                        "rule": "Primary: Priority Ranking",
                        "status": "Decisive",
                        "details": f"Priority {task.priority_label} ({task.priority}) is higher than '{runner_up.title}' ({runner_up.priority})."
                    })
                elif task.priority == runner_up.priority:
                    criteria.append({
                        "rule": "Primary: Priority Ranking",
                        "status": "Tied",
                        "details": f"Equal priority ({task.priority}). Resolving by deadline."
                    })
                    if task.deadline < runner_up.deadline:
                        criteria.append({
                            "rule": "Tie-Breaker 1: Earliest Deadline",
                            "status": "Decisive",
                            "details": f"Earlier deadline than runner-up: {task.time_remaining_str(now)}."
                        })
            else:
                criteria.append({
                    "rule": "Primary: Priority Ranking",
                    "status": "Decisive",
                    "details": "Single active task in the priority queue."
                })

        return {
            "has_task": True,
            "task_id": task.task_id,
            "title": task.title,
            "policy": self._policy.value,
            "policy_name": "Earliest Deadline First (EDF)" if self._policy == SchedulingPolicy.EARLIEST_DEADLINE else "Priority First",
            "primary_reason": primary_reason,
            "criteria": criteria,
            "runner_up_title": runner_up.title if runner_up else None,
            "total_in_queue": len(queue),
        }

    def check_capacity_warning(self, work_window_minutes: Optional[int] = None) -> Dict[str, Any]:
        """
        Heuristic capacity estimation: compares total estimated duration of active tasks
        against the user's defined work window or upcoming deadline window.
        """
        if work_window_minutes is None:
            try:
                work_window_minutes = int(self.repo.get_setting("capacity_work_window_minutes", "180"))
            except ValueError:
                work_window_minutes = 180

        active_tasks = self.repo.get_active_tasks()
        total_estimated = sum(t.estimated_minutes for t in active_tasks)
        overdue_count = sum(1 for t in active_tasks if t.is_overdue())

        has_overload = total_estimated > work_window_minutes
        deficit = total_estimated - work_window_minutes if has_overload else 0

        return {
            "work_window_minutes": work_window_minutes,
            "total_estimated_minutes": total_estimated,
            "active_task_count": len(active_tasks),
            "overdue_count": overdue_count,
            "has_overload": has_overload,
            "deficit_minutes": deficit,
            "utilization_pct": round((total_estimated / work_window_minutes * 100), 1) if work_window_minutes > 0 else 100,
            "message": (
                f"Active task effort ({total_estimated} min) exceeds your available work window ({work_window_minutes} min) by {deficit} min."
                if has_overload
                else f"Active load ({total_estimated} min) fits within your available work window ({work_window_minutes} min)."
            ),
            "disclaimer": "Rough capacity estimate assuming single-threaded focus without preemption; does not guarantee timetable optimality."
        }

    def get_deadline_rail(self) -> List[Dict[str, Any]]:
        """
        Groups upcoming active tasks chronologically for the pressure strip.
        """
        tasks = self.repo.get_active_tasks()
        now = datetime.now(timezone.utc)
        rail = []

        for t in tasks:
            urgency = t.urgency_category(now)
            rail.append({
                "task_id": t.task_id,
                "title": t.title,
                "deadline": t.deadline,
                "deadline_str": t.deadline.strftime("%b %d, %H:%M"),
                "time_remaining": t.time_remaining_str(now),
                "urgency": urgency,
                "priority": t.priority,
                "estimated_minutes": t.estimated_minutes,
            })
        return rail

