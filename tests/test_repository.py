"""
Unit tests for TaskRepository and SQLite persistence.
"""
import pytest
from datetime import datetime, timezone, timedelta
from core.models import Task
from core.repository import TaskRepository


@pytest.fixture
def repo():
    return TaskRepository(":memory:")


def test_crud_lifecycle(repo):
    now = datetime.now(timezone.utc)
    task = Task(
        task_id="TSK-001",
        title="Implement Dijkstra Algorithm",
        notes="Use indexed min-heap for O((V + E) log V)",
        deadline=now + timedelta(days=1),
        estimated_minutes=45,
        priority=4,
    )

    # Insert
    repo.add_task(task)
    retrieved = repo.get_task("TSK-001")
    assert retrieved is not None
    assert retrieved.title == "Implement Dijkstra Algorithm"
    assert retrieved.priority == 4
    assert retrieved.status == "active"

    # Update
    retrieved.title = "Implement Dijkstra with Fibonacci Heap"
    retrieved.priority = 5
    repo.update_task(retrieved)

    updated = repo.get_task("TSK-001")
    assert updated.title == "Implement Dijkstra with Fibonacci Heap"
    assert updated.priority == 5
    assert updated.version == 2

    # Delete
    deleted = repo.delete_task("TSK-001")
    assert deleted is True
    assert repo.get_task("TSK-001") is None


def test_model_validation():
    now = datetime.now(timezone.utc)

    # Blank title should raise ValueError
    with pytest.raises(ValueError):
        Task(task_id="ERR-1", title="   ", deadline=now)

    # Non-positive duration should raise ValueError
    with pytest.raises(ValueError):
        Task(task_id="ERR-2", title="Valid title", estimated_minutes=0, deadline=now)

    # Priority outside 1..5 should raise ValueError
    with pytest.raises(ValueError):
        Task(task_id="ERR-3", title="Valid title", priority=6, deadline=now)


def test_seed_and_reset(repo):
    count = repo.seed_demo_data(force=True)
    assert count > 0

    all_tasks = repo.get_all_tasks()
    assert len(all_tasks) == count

    active = repo.get_active_tasks()
    assert len(active) > 0

    repo.reset_all()
    assert len(repo.get_all_tasks()) == 0


def test_settings_storage(repo):
    repo.set_setting("ordering_policy", "priority_first")
    val = repo.get_setting("ordering_policy")
    assert val == "priority_first"

    fallback = repo.get_setting("non_existent_key", "default_val")
    assert fallback == "default_val"

