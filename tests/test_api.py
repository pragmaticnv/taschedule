"""
Integration tests for TICKLINE web routes and API endpoints.
"""
import pytest
from starlette.testclient import TestClient
from datetime import datetime, timezone, timedelta
from app import app, repo, scheduler


@pytest.fixture
def client():
    # Reset repo to demo state for predictable testing
    repo.seed_demo_data(force=True)
    scheduler.rebuild_heap()
    return TestClient(app)


def test_root_view(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "TICKLINE" in response.text


def test_queue_view(client):
    response = client.get("/queue")
    assert response.status_code == 200
    assert "Workbench" in response.text


def test_heap_lab_view(client):
    response = client.get("/heap-lab")
    assert response.status_code == 200
    assert "Heap Laboratory" in response.text
    assert "SATISFIED &amp; SOUND" in response.text or "SATISFIED" in response.text


def test_create_task_flow(client):
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=3)).strftime("%Y-%m-%dT12:00")
    response = client.post("/tasks/new", data={
        "task_id": "TSK-TEST-99",
        "title": "Integration Test Task",
        "notes": "Testing route",
        "deadline": future,
        "estimated_minutes": "30",
        "priority": "4"
    }, follow_redirects=False)
    assert response.status_code == 303

    # Check task exists in repository
    t = repo.get_task("TSK-TEST-99")
    assert t is not None
    assert t.title == "Integration Test Task"


def test_complete_next_action(client):
    top_before = scheduler.peek_next()
    assert top_before is not None

    response = client.post("/tasks/complete-next", follow_redirects=False)
    assert response.status_code == 303

    completed = repo.get_task(top_before.task_id)
    assert completed.status == "completed"


def test_api_endpoints(client):
    # API Queue
    res_q = client.get("/api/queue")
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert "tasks" in data_q
    assert data_q["count"] > 0

    # API Heap
    res_h = client.get("/api/heap")
    assert res_h.status_code == 200
    data_h = res_h.json()
    assert data_h["invariant_valid"] is True
    assert len(data_h["nodes"]) > 0

    # API State (Full reactive payload)
    res_s = client.get("/api/state")
    assert res_s.status_code == 200
    data_s = res_s.json()
    assert "next_task" in data_s
    assert "heap" in data_s
    assert "ranked_queue" in data_s


def test_api_json_create_and_complete(client):
    now = datetime.now(timezone.utc)
    res_create = client.post("/api/tasks", json={
        "title": "Super Urgent Lab Submission",
        "deadline": (now + timedelta(hours=1)).isoformat(),
        "priority": 5,
        "estimated_minutes": 30,
        "notes": "Testing JSON API"
    })
    assert res_create.status_code == 200
    data = res_create.json()
    assert data["success"] is True
    assert data["task"]["priority"] == 5

    # Complete next via JSON API
    res_comp = client.post("/api/tasks/complete-next")
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["success"] is True

