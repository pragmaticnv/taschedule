"""
TICKLINE: Task Scheduler with Deadlines
FastAPI Web Application Entry Point & Controller
Advanced Data Structures Mini-Project (Project 17)
"""
import os
import sys

# Ensure current project directory takes precedence in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.models import Task
from core.priority_queue import MinHeap
from core.repository import TaskRepository, DEFAULT_DB_PATH
from core.scheduler import Scheduler, SchedulingPolicy

STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="TICKLINE - Task Scheduler with Deadlines", version="1.0.0")

# Static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Core State Initialization
repo = TaskRepository(DEFAULT_DB_PATH)
# If empty, seed initial demo tasks
if len(repo.get_all_tasks()) == 0:
    repo.seed_demo_data()

scheduler = Scheduler(repo)

# Receipt cache for user feedback
last_receipt: Optional[Dict[str, Any]] = None


def get_common_context(request: Request, active_page: str) -> Dict[str, Any]:
    active_tasks = repo.get_active_tasks()
    all_tasks = repo.get_all_tasks()
    completed_tasks = repo.get_completed_tasks()

    policy_name = (
        "Earliest Deadline First (EDF)"
        if scheduler.policy == SchedulingPolicy.EARLIEST_DEADLINE
        else "Priority First (Hierarchy)"
    )

    return {
        "request": request,
        "active_page": active_page,
        "now": datetime.now(timezone.utc),
        "active_count": len(active_tasks),
        "total_count": len(all_tasks),
        "completed_count": len(completed_tasks),
        "current_policy": scheduler.policy.value,
        "current_policy_name": policy_name,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    context = get_common_context(request, active_page="queue")
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.get("/queue", response_class=HTMLResponse)
async def queue_view(request: Request):
    context = get_common_context(request, active_page="queue")
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.post("/tasks/complete-next")
async def complete_next():
    global last_receipt
    completed, new_next = scheduler.complete_next_task()
    if completed:
        last_receipt = {
            "task_id": completed.task_id,
            "title": completed.title,
            "completed_at": completed.completed_at.strftime("%H:%M:%S UTC") if completed.completed_at else "Now",
            "new_top_id": new_next.task_id if new_next else "None",
            "new_top_title": new_next.title if new_next else "Queue Empty",
        }
        return RedirectResponse(url="/queue?receipt=1", status_code=303)
    return RedirectResponse(url="/queue", status_code=303)


@app.post("/tasks/{task_id}/complete")
async def complete_specific(task_id: str):
    global last_receipt
    completed = repo.complete_task(task_id)
    scheduler.rebuild_heap()
    if completed:
        last_receipt = {
            "task_id": completed.task_id,
            "title": completed.title,
            "completed_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        }
        return RedirectResponse(url="/queue?receipt=1", status_code=303)
    return RedirectResponse(url="/queue", status_code=303)


@app.post("/tasks/{task_id}/reopen")
async def reopen_specific(task_id: str):
    repo.reopen_task(task_id)
    scheduler.rebuild_heap()
    return RedirectResponse(url="/queue", status_code=303)


@app.post("/tasks/{task_id}/delete")
async def delete_specific(task_id: str):
    repo.delete_task(task_id)
    scheduler.rebuild_heap()
    return RedirectResponse(url="/all", status_code=303)


@app.get("/all", response_class=HTMLResponse)
async def all_tasks_view(
    request: Request,
    q: Optional[str] = None,
    status: Optional[str] = "all",
    priority: Optional[str] = "all",
):
    context = get_common_context(request, active_page="all")
    tasks = repo.get_all_tasks()

    query_str = (q or "").strip().lower()
    filtered = []

    for t in tasks:
        # Status filter
        if status == "active" and t.status != "active":
            continue
        if status == "completed" and t.status != "completed":
            continue

        # Priority filter
        if priority and priority != "all":
            try:
                if t.priority != int(priority):
                    continue
            except ValueError:
                pass

        # Text query filter
        if query_str:
            in_title = query_str in t.title.lower()
            in_id = query_str in t.task_id.lower()
            in_notes = query_str in t.notes.lower()
            if not (in_title or in_id or in_notes):
                continue

        filtered.append(t)

    context.update({
        "tasks": filtered,
        "query": q or "",
        "status_filter": status,
        "priority_filter": priority,
    })
    return templates.TemplateResponse(request=request, name="all_tasks.html", context=context)


@app.get("/tasks/new", response_class=HTMLResponse)
async def new_task_form(request: Request):
    context = get_common_context(request, active_page="new")
    # Default deadline: tomorrow at 17:00 UTC
    default_dt = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT17:00")
    
    # Auto ID generator
    next_num = len(repo.get_all_tasks()) + 101
    prefill_id = f"TSK-{next_num}"

    context.update({
        "is_edit": False,
        "task": None,
        "deadline_val": default_dt,
        "prefill_id": prefill_id,
        "error": None,
    })
    return templates.TemplateResponse(request=request, name="task_form.html", context=context)


@app.post("/tasks/new", response_class=HTMLResponse)
async def create_task(
    request: Request,
    title: str = Form(...),
    notes: Optional[str] = Form(""),
    deadline: str = Form(...),
    estimated_minutes: int = Form(...),
    priority: int = Form(...),
    task_id: Optional[str] = Form(None),
):
    try:
        # Validate task_id or auto-generate
        tid = (task_id or "").strip()
        if not tid:
            tid = f"TSK-{len(repo.get_all_tasks()) + 101}"

        # Check uniqueness
        if repo.get_task(tid):
            tid = f"TSK-{len(repo.get_all_tasks()) + 102}"

        # Parse deadline
        dt = datetime.fromisoformat(deadline)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        new_t = Task(
            task_id=tid,
            title=title,
            notes=notes or "",
            deadline=dt,
            estimated_minutes=estimated_minutes,
            priority=priority,
            status="active",
        )
        repo.add_task(new_t)
        # Sift into heap
        scheduler.rebuild_heap()
        return RedirectResponse(url="/queue", status_code=303)

    except Exception as e:
        context = get_common_context(request, active_page="new")
        context.update({
            "is_edit": False,
            "task": None,
            "deadline_val": deadline,
            "prefill_id": task_id,
            "error": str(e),
        })
        return templates.TemplateResponse(request=request, name="task_form.html", context=context)


@app.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
async def edit_task_form(request: Request, task_id: str):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    context = get_common_context(request, active_page="all")
    deadline_val = task.deadline.strftime("%Y-%m-%dT%H:%M")

    context.update({
        "is_edit": True,
        "task": task,
        "deadline_val": deadline_val,
        "error": None,
    })
    return templates.TemplateResponse(request=request, name="task_form.html", context=context)


@app.post("/tasks/{task_id}/edit", response_class=HTMLResponse)
async def update_task(
    request: Request,
    task_id: str,
    title: str = Form(...),
    notes: Optional[str] = Form(""),
    deadline: str = Form(...),
    estimated_minutes: int = Form(...),
    priority: int = Form(...),
    status: str = Form("active"),
):
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        dt = datetime.fromisoformat(deadline)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        task.title = title
        task.notes = notes or ""
        task.deadline = dt
        task.estimated_minutes = estimated_minutes
        task.priority = priority
        task.status = status

        repo.update_task(task)
        scheduler.rebuild_heap()
        return RedirectResponse(url="/queue", status_code=303)

    except Exception as e:
        context = get_common_context(request, active_page="all")
        context.update({
            "is_edit": True,
            "task": task,
            "deadline_val": deadline,
            "error": str(e),
        })
        return templates.TemplateResponse(request=request, name="task_form.html", context=context)


@app.get("/heap-lab", response_class=HTMLResponse)
async def heap_lab_view(request: Request):
    context = get_common_context(request, active_page="heap_lab")

    invariant_valid, invariant_error = scheduler.heap.verify_heap_invariant()
    heap_nodes = scheduler.heap.get_array_representation()
    trace_log = scheduler.heap.get_trace_log()
    heap_size = scheduler.heap.size()
    tree_height = int(math.floor(math.log2(heap_size))) if heap_size > 0 else 0

    context.update({
        "invariant_valid": invariant_valid,
        "invariant_error": invariant_error,
        "heap_nodes": heap_nodes,
        "trace_log": trace_log,
        "heap_size": heap_size,
        "tree_height": tree_height,
    })
    return templates.TemplateResponse(request=request, name="heap_lab.html", context=context)


@app.get("/completed", response_class=HTMLResponse)
async def completed_view(request: Request):
    context = get_common_context(request, active_page="completed")
    completed_tasks = repo.get_completed_tasks()
    context.update({
        "tasks": completed_tasks,
    })
    return templates.TemplateResponse(request=request, name="completed.html", context=context)


@app.get("/settings", response_class=HTMLResponse)
async def settings_view(request: Request, saved: Optional[str] = None):
    context = get_common_context(request, active_page="settings")
    work_window = repo.get_setting("capacity_work_window_minutes", "180")

    context.update({
        "work_window_minutes": work_window,
        "saved": saved is not None,
    })
    return templates.TemplateResponse(request=request, name="settings.html", context=context)


@app.post("/settings")
async def save_settings(
    ordering_policy: str = Form(...),
    work_window_minutes: int = Form(180),
):
    scheduler.policy = SchedulingPolicy(ordering_policy)
    repo.set_setting("capacity_work_window_minutes", str(work_window_minutes))
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@app.post("/demo/seed")
async def seed_demo():
    repo.seed_demo_data(force=True)
    scheduler.rebuild_heap()
    return RedirectResponse(url="/queue", status_code=303)


@app.post("/demo/reset")
async def reset_demo():
    repo.reset_all()
    scheduler.rebuild_heap()
    return RedirectResponse(url="/queue", status_code=303)


# --- REST API endpoints for modern reactive glassmorphic UI ---
@app.get("/api/state")
async def api_state():
    """Returns full scheduler, queue, heap, and capacity state in one fast JSON payload."""
    active_tasks = repo.get_active_tasks()
    all_tasks = repo.get_all_tasks()
    completed_tasks = repo.get_completed_tasks()
    
    next_task = scheduler.peek_next()
    explanation = scheduler.explain_recommendation(next_task)
    ranked_queue = scheduler.get_ranked_queue()
    deadline_rail = scheduler.get_deadline_rail()
    capacity = scheduler.check_capacity_warning()
    
    valid, err = scheduler.heap.verify_heap_invariant()
    heap_nodes = scheduler.heap.get_array_representation()
    trace_log = scheduler.heap.get_trace_log()
    heap_size = scheduler.heap.size()
    tree_height = int(math.floor(math.log2(heap_size))) if heap_size > 0 else 0

    return {
        "policy": scheduler.policy.value,
        "policy_name": "Earliest Deadline First (EDF)" if scheduler.policy == SchedulingPolicy.EARLIEST_DEADLINE else "Priority First (Hierarchy)",
        "active_count": len(active_tasks),
        "total_count": len(all_tasks),
        "completed_count": len(completed_tasks),
        "next_task": next_task.to_dict() if next_task else None,
        "explanation": explanation,
        "ranked_queue": [t.to_dict() for t in ranked_queue],
        "completed_tasks": [t.to_dict() for t in completed_tasks],
        "deadline_rail": deadline_rail,
        "capacity": capacity,
        "heap": {
            "size": heap_size,
            "tree_height": tree_height,
            "invariant_valid": valid,
            "invariant_error": err,
            "nodes": [{
                "index": n["index"],
                "key": str(n["key"]),
                "task": n["value"].to_dict(),
                "parent_index": n["parent_index"],
                "left_child_index": n["left_child_index"],
                "right_child_index": n["right_child_index"],
                "level": n["level"],
                "is_root": n["is_root"],
                "is_leaf": n["is_leaf"],
            } for n in heap_nodes],
            "trace_log": [{
                "operation": ev.operation,
                "timestamp": ev.timestamp,
                "comparisons": ev.comparisons,
                "swaps": ev.swaps,
                "explanation": ev.explanation,
                "item_label": ev.item_label,
            } for ev in trace_log],
        }
    }


@app.post("/api/tasks")
async def api_create_task(request: Request):
    """Creates a task from JSON and inserts into the binary min-heap."""
    try:
        data = await request.json()
        title = data.get("title", "").strip()
        if not title:
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        
        deadline_str = data.get("deadline")
        if not deadline_str:
            raise HTTPException(status_code=400, detail="Deadline is required")
        
        dt = datetime.fromisoformat(deadline_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        estimated_minutes = int(data.get("estimated_minutes", 30))
        priority = int(data.get("priority", 3))
        notes = data.get("notes", "").strip()
        
        task_id = data.get("task_id", "").strip()
        if not task_id or repo.get_task(task_id):
            task_id = f"TSK-{len(repo.get_all_tasks()) + 101}"
            while repo.get_task(task_id):
                task_id = f"TSK-{int(task_id.split('-')[1]) + 1}"
        
        task = Task(
            task_id=task_id,
            title=title,
            notes=notes,
            deadline=dt,
            estimated_minutes=estimated_minutes,
            priority=priority,
            status="active"
        )
        repo.add_task(task)
        scheduler.rebuild_heap()
        return {"success": True, "task": task.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}")
async def api_update_task(task_id: str, request: Request):
    """Updates a task and rebuilds the min-heap."""
    task = repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    try:
        data = await request.json()
        if "title" in data:
            task.title = data["title"].strip()
        if "notes" in data:
            task.notes = data["notes"].strip()
        if "deadline" in data:
            dt = datetime.fromisoformat(data["deadline"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            task.deadline = dt
        if "estimated_minutes" in data:
            task.estimated_minutes = int(data["estimated_minutes"])
        if "priority" in data:
            task.priority = int(data["priority"])
        if "status" in data:
            task.status = data["status"]
            
        repo.update_task(task)
        scheduler.rebuild_heap()
        return {"success": True, "task": task.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/tasks/{task_id}")
async def api_delete_task(task_id: str):
    """Deletes task and rebuilds min-heap."""
    deleted = repo.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    scheduler.rebuild_heap()
    return {"success": True, "task_id": task_id}


@app.post("/api/tasks/{task_id}/complete")
async def api_complete_task(task_id: str):
    """Completes a specific task."""
    completed = repo.complete_task(task_id)
    if not completed:
        raise HTTPException(status_code=404, detail="Task not found")
    scheduler.rebuild_heap()
    return {"success": True, "completed": completed.to_dict()}


@app.post("/api/tasks/{task_id}/reopen")
async def api_reopen_task(task_id: str):
    """Reopens a completed task and reinserts into min-heap."""
    reopened = repo.reopen_task(task_id)
    if not reopened:
        raise HTTPException(status_code=404, detail="Task not found")
    scheduler.rebuild_heap()
    return {"success": True, "reopened": reopened.to_dict()}


@app.post("/api/tasks/complete-next")
async def api_complete_next():
    """Extracts top element from heap in O(log n)."""
    completed, new_next = scheduler.complete_next_task()
    if not completed:
        return {"success": False, "message": "Queue is empty"}
    return {
        "success": True,
        "completed": completed.to_dict(),
        "new_next": new_next.to_dict() if new_next else None,
    }


@app.post("/api/settings")
async def api_update_settings(request: Request):
    data = await request.json()
    if "ordering_policy" in data:
        scheduler.policy = SchedulingPolicy(data["ordering_policy"])
    if "work_window_minutes" in data:
        repo.set_setting("capacity_work_window_minutes", str(data["work_window_minutes"]))
    return {"success": True, "policy": scheduler.policy.value}


@app.post("/api/demo/seed")
async def api_seed_demo():
    count = repo.seed_demo_data(force=True)
    scheduler.rebuild_heap()
    return {"success": True, "count": count}


@app.post("/api/demo/reset")
async def api_reset_demo():
    repo.reset_all()
    scheduler.rebuild_heap()
    return {"success": True}


# --- Legacy / Template Endpoints ---
@app.get("/api/queue")
async def api_queue():
    ranked = scheduler.get_ranked_queue()
    return {
        "count": len(ranked),
        "policy": scheduler.policy.value,
        "tasks": [t.to_dict() for t in ranked],
    }


@app.get("/api/heap")
async def api_heap():
    valid, err = scheduler.heap.verify_heap_invariant()
    return {
        "size": scheduler.heap.size(),
        "invariant_valid": valid,
        "invariant_error": err,
        "nodes": scheduler.heap.get_array_representation(),
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("  TICKLINE: Task Scheduler with Deadlines")
    print("  Advanced Data Structures Mini-Project (Project 17)")
    print("  Starting local server at http://127.0.0.1:8000")
    print("="*60 + "\n")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
