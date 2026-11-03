"""
Unit and integration tests for Scheduler policies, tie-breakers, and explanations.
"""
import pytest
from datetime import datetime, timezone, timedelta
from core.models import Task
from core.repository import TaskRepository
from core.scheduler import Scheduler, SchedulingPolicy


@pytest.fixture
def repo():
    r = TaskRepository(":memory:")
    return r


def test_earliest_deadline_policy(repo):
    now = datetime.now(timezone.utc)
    t1 = Task("T1", "Late task", deadline=now + timedelta(hours=10), priority=5)
    t2 = Task("T2", "Soon task", deadline=now + timedelta(hours=2), priority=2)
    t3 = Task("T3", "Tomorrow task", deadline=now + timedelta(hours=24), priority=4)

    repo.add_task(t1)
    repo.add_task(t2)
    repo.add_task(t3)

    scheduler = Scheduler(repo)
    top = scheduler.peek_next()
    assert top is not None
    assert top.task_id == "T2"

    queue = scheduler.get_ranked_queue()
    assert [t.task_id for t in queue] == ["T2", "T1", "T3"]


def test_deadline_tie_breaker_priority(repo):
    now = datetime.now(timezone.utc)
    same_deadline = now + timedelta(hours=5)

    t_low = Task("T_LOW", "Low priority", deadline=same_deadline, priority=2)
    t_high = Task("T_HIGH", "High priority", deadline=same_deadline, priority=5)

    repo.add_task(t_low)
    repo.add_task(t_high)

    scheduler = Scheduler(repo)
    top = scheduler.peek_next()
    assert top.task_id == "T_HIGH"


def test_priority_first_policy_switch(repo):
    now = datetime.now(timezone.utc)
    t_deadline_soon = Task("T_SOON", "Due in 1 hour", deadline=now + timedelta(hours=1), priority=2)
    t_urgent_prio = Task("T_PRIO", "Critical task", deadline=now + timedelta(hours=10), priority=5)

    repo.add_task(t_deadline_soon)
    repo.add_task(t_urgent_prio)

    scheduler = Scheduler(repo)
    assert scheduler.peek_next().task_id == "T_SOON"

    # Switch policy to Priority First
    scheduler.policy = SchedulingPolicy.PRIORITY_FIRST
    assert scheduler.peek_next().task_id == "T_PRIO"


def test_complete_and_reopen_flow(repo):
    now = datetime.now(timezone.utc)
    t1 = Task("T1", "First", deadline=now + timedelta(hours=1), priority=3)
    t2 = Task("T2", "Second", deadline=now + timedelta(hours=2), priority=3)

    repo.add_task(t1)
    repo.add_task(t2)

    scheduler = Scheduler(repo)
    assert scheduler.peek_next().task_id == "T1"

    completed, new_top = scheduler.complete_next_task()
    assert completed.task_id == "T1"
    assert completed.status == "completed"
    assert new_top.task_id == "T2"
    assert scheduler.peek_next().task_id == "T2"

    # Reopen T1
    repo.reopen_task("T1")
    scheduler.rebuild_heap()
    assert scheduler.peek_next().task_id == "T1"


def test_why_this_task_explanation(repo):
    now = datetime.now(timezone.utc)
    t1 = Task("T1", "Urgent bug", deadline=now + timedelta(hours=1), priority=5)
    t2 = Task("T2", "Refactor", deadline=now + timedelta(hours=5), priority=3)

    repo.add_task(t1)
    repo.add_task(t2)

    scheduler = Scheduler(repo)
    exp = scheduler.explain_recommendation()
    assert exp["has_task"] is True
    assert exp["task_id"] == "T1"
    assert len(exp["criteria"]) > 0
    assert "Primary: Earliest Deadline" in exp["criteria"][0]["rule"]


def test_capacity_warning_detection(repo):
    now = datetime.now(timezone.utc)
    # Total effort: 120 + 90 = 210 minutes
    repo.add_task(Task("T1", "Task 1", deadline=now + timedelta(hours=2), estimated_minutes=120, priority=3))
    repo.add_task(Task("T2", "Task 2", deadline=now + timedelta(hours=3), estimated_minutes=90, priority=3))

    scheduler = Scheduler(repo)
    # Work window: 180 min -> should trigger overload
    cap = scheduler.check_capacity_warning(work_window_minutes=180)
    assert cap["has_overload"] is True
    assert cap["deficit_minutes"] == 30
    assert cap["total_estimated_minutes"] == 210

