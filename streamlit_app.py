"""
TICKLINE: Task Scheduler with Deadlines (Streamlit Edition)
Project 17 - Advanced Data Structures Mini-Project
"""
import os
import sys

# Ensure current project directory takes precedence
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
from datetime import datetime, timezone, timedelta
import math

from core.models import Task
from core.repository import TaskRepository, DEFAULT_DB_PATH
from core.scheduler import Scheduler, SchedulingPolicy

st.set_page_config(
    page_title="TICKLINE — Task Scheduler with Deadlines",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Crafted Instrument Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&family=Inter:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        background-color: #F8F6F0;
        color: #1C1D1B;
    }
    .stApp {
        background-color: #F8F6F0;
    }
    h1, h2, h3 {
        font-family: 'Newsreader', Georgia, serif !important;
        font-weight: 600;
        color: #1C1D1B;
    }
    .mono-badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        background: #ECE9DF;
        padding: 3px 8px;
        border: 1px solid #D5D0C3;
        border-radius: 2px;
    }
    .vermilion-callout {
        border-left: 4px solid #C84C36;
        background: #FFFFFF;
        padding: 16px 20px;
        border-radius: 2px;
        border-top: 1px solid #E5E1D6;
        border-right: 1px solid #E5E1D6;
        border-bottom: 1px solid #E5E1D6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "repo" not in st.session_state:
    st.session_state.repo = TaskRepository(DEFAULT_DB_PATH)
    if len(st.session_state.repo.get_all_tasks()) == 0:
        st.session_state.repo.seed_demo_data()

repo = st.session_state.repo

if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler(repo)

scheduler = st.session_state.scheduler

# Sidebar Navigation
st.sidebar.markdown("""
<div style="padding: 10px 0 16px;">
    <h2 style="margin: 0; font-family: 'Newsreader', serif; font-size: 24px; color: #1C1D1B;">
        <span style="color: #C84C36;">■</span> TICKLINE
    </h2>
    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #5C605C; text-transform: uppercase;">
        Project 17 &bull; Min-Heap Queue
    </div>
</div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navigation Rail",
    ["Workbench & Queue", "All Tasks", "Quick Capture", "Heap Laboratory", "Completed Archive", "Settings & Demo"],
    label_visibility="collapsed"
)

active_tasks = repo.get_active_tasks()
completed_tasks = repo.get_completed_tasks()

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #5C605C;">
    <div>Policy: <strong>{scheduler.policy.value}</strong></div>
    <div>Active in Heap: <strong>{len(active_tasks)}</strong></div>
    <div>Completed: <strong>{len(completed_tasks)}</strong></div>
    <div style="margin-top: 8px; color: #2D6A4F;">Heap Invariant: O(log n)</div>
</div>
""", unsafe_allow_html=True)

# ----------------- WORKBENCH & QUEUE -----------------
if menu == "Workbench & Queue":
    st.title("Queue Workbench")
    st.caption("Deterministic priority queue backed by binary min-heap. Ordered by active comparator.")

    # Capacity warning
    cap = scheduler.check_capacity_warning()
    if cap["has_overload"]:
        st.warning(f"⚠️ **Capacity Alert:** Active task effort ({cap['total_estimated_minutes']} min) exceeds work window ({cap['work_window_minutes']} min) by {cap['deficit_minutes']} min. (Heuristic single-threaded capacity estimate).")

    # Next Up
    next_task = scheduler.peek_next()
    if next_task:
        st.markdown(f"""
        <div class="vermilion-callout">
            <div style="font-family: 'IBM Plex Mono', monospace; font-size: 11px; text-transform: uppercase; color: #C84C36; font-weight: 700;">
                ▼ Root Element (Index 0 &bull; O(1) Peek)
            </div>
            <h2 style="margin: 8px 0; font-size: 26px;">{next_task.title}</h2>
            <p style="color: #5C605C; font-size: 13px;">{next_task.notes or 'No additional notes provided.'}</p>
            <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap;">
                <span class="mono-badge">ID: {next_task.task_id}</span>
                <span class="mono-badge">Priority: {next_task.priority_label} (Level {next_task.priority})</span>
                <span class="mono-badge">Deadline: {next_task.deadline.strftime('%Y-%m-%d %H:%M UTC')}</span>
                <span class="mono-badge">{next_task.time_remaining_str()}</span>
                <span class="mono-badge">Effort: {next_task.estimated_minutes}m</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Why this task?
        exp = scheduler.explain_recommendation(next_task)
        with st.expander("🔍 Why This Task First? (Algorithmic Comparator Proof)", expanded=True):
            st.markdown(f"**Policy:** {exp['policy_name']}")
            st.markdown(f"**Determinant:** {exp['primary_reason']}")
            for c in exp["criteria"]:
                st.markdown(f"- **{c['status']}**: {c['rule']} — *{c['details']}*")
            if exp["runner_up_title"]:
                st.caption(f"Runner-up contender: *\"{exp['runner_up_title']}\"* was outranked on comparator key.")

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("✓ Complete Next Up", type="primary"):
                completed, _ = scheduler.complete_next_task()
                st.success(f"Completed '{completed.title}'! Popped from heap in O(log n).")
                st.rerun()

    else:
        st.info("Queue is currently empty. Add tasks or seed demo data.")

    # Ranked Active Queue
    ranked_queue = scheduler.get_ranked_queue()
    if ranked_queue:
        st.markdown("### Ranked Priority Queue (Sorted Projection • O(n log n))")
        data = []
        for idx, t in enumerate(ranked_queue, start=1):
            data.append({
                "Rank": f"#{idx}",
                "Task ID": t.task_id,
                "Title": t.title,
                "Urgency": t.time_remaining_str(),
                "Deadline (UTC)": t.deadline.strftime("%Y-%m-%d %H:%M"),
                "Priority": t.priority_label,
                "Effort": f"{t.estimated_minutes}m",
            })
        st.dataframe(data, use_container_width=True)

# ----------------- HEAP LABORATORY -----------------
elif menu == "Heap Laboratory":
    st.title("Heap Laboratory")
    st.caption("Live structural inspection of the 0-indexed binary min-heap array, invariant checks, and operation trace.")

    valid, err = scheduler.heap.verify_heap_invariant()
    heap_size = scheduler.heap.size()
    tree_height = int(math.floor(math.log2(heap_size))) if heap_size > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Heap Invariant", "Verified & Sound" if valid else "Violated")
    col2.metric("Total Elements (n)", heap_size)
    col3.metric("Tree Height", f"⌊log₂({heap_size})⌋ = {tree_height}")

    st.markdown("### Sequential Array Representation: `A[0 .. n-1]`")
    nodes = scheduler.heap.get_array_representation()
    if nodes:
        cols = st.columns(min(len(nodes), 4))
        for i, node in enumerate(nodes):
            with cols[i % min(len(nodes), 4)]:
                st.markdown(f"""
                <div style="background: {'#FAF2F0' if node['is_root'] else '#FFFFFF'}; border: 1px solid {'#C84C36' if node['is_root'] else '#D5D0C3'}; padding: 10px; margin-bottom: 10px;">
                    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: {'#C84C36' if node['is_root'] else '#5C605C'}; font-weight: 700;">
                        Index [{node['index']}] {'(ROOT)' if node['is_root'] else ''} &bull; Lvl {node['level']}
                    </div>
                    <div style="font-weight: 600; font-size: 13px; margin: 4px 0;">{node['value'].title}</div>
                    <div style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #5C605C;">
                        Parent: {node['parent_index'] if node['parent_index'] is not None else 'None'}<br>
                        Children: [{node['left_child_index']}, {node['right_child_index']}]
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("### Operational Event Trace Log")
    trace = scheduler.heap.get_trace_log()
    if trace:
        trace_data = [{
            "Timestamp": ev.timestamp,
            "Operation": ev.operation,
            "Comparisons": ev.comparisons,
            "Swaps": len(ev.swaps),
            "Explanation": ev.explanation
        } for ev in trace]
        st.dataframe(trace_data, use_container_width=True)

    st.markdown("### Asymptotic Complexity Reference")
    st.markdown("""
    - **Peek Root:** $O(1)$
    - **Insert (Sift-Up):** $O(\\log n)$
    - **Extract-Min (Sift-Down):** $O(\\log n)$
    - **Bottom-Up Heapify:** $O(n)$
    - **Sorted Projection:** $O(n \\log n)$
    """)

# ----------------- QUICK CAPTURE -----------------
elif menu == "Quick Capture":
    st.title("Quick Capture Task")
    with st.form("new_task_form"):
        title = st.text_input("Task Title *", placeholder="e.g. Implement Dijkstra's Algorithm with Heap")
        notes = st.text_area("Notes", placeholder="Optional details, academic requirements...")
        c1, c2 = st.columns(2)
        with c1:
            deadline_date = st.date_input("Deadline Date", datetime.now().date() + timedelta(days=1))
            deadline_time = st.time_input("Deadline Time", datetime.strptime("17:00", "%H:%M").time())
        with c2:
            priority = st.selectbox("Priority Level", [5, 4, 3, 2, 1], index=2, format_func=lambda x: f"P{x} — {Task(task_id='X', title='X', priority=x).priority_label}")
            estimated_minutes = st.number_input("Estimated Minutes", min_value=5, max_value=720, value=45, step=5)
        
        submitted = st.form_submit_button("Insert Into Heap Priority Queue", type="primary")
        if submitted:
            if not title.strip():
                st.error("Title cannot be blank!")
            else:
                deadline_dt = datetime.combine(deadline_date, deadline_time).replace(tzinfo=timezone.utc)
                new_id = f"TSK-{len(repo.get_all_tasks()) + 101}"
                task = Task(
                    task_id=new_id,
                    title=title,
                    notes=notes,
                    deadline=deadline_dt,
                    estimated_minutes=estimated_minutes,
                    priority=priority,
                )
                repo.add_task(task)
                scheduler.rebuild_heap()
                st.success(f"Task '{task.title}' inserted and sifted into binary min-heap!")
                st.rerun()

# ----------------- ALL TASKS -----------------
elif menu == "All Tasks":
    st.title("All Tasks Inventory")
    tasks = repo.get_all_tasks()
    all_data = []
    for t in tasks:
        all_data.append({
            "ID": t.task_id,
            "Title": t.title,
            "Status": t.status,
            "Priority": t.priority_label,
            "Deadline (UTC)": t.deadline.strftime("%Y-%m-%d %H:%M"),
            "Effort": f"{t.estimated_minutes}m",
            "Version": f"v{t.version}",
        })
    st.dataframe(all_data, use_container_width=True)

# ----------------- COMPLETED ARCHIVE -----------------
elif menu == "Completed Archive":
    st.title("Completed Tasks Archive")
    comp = repo.get_completed_tasks()
    if comp:
        for t in comp:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**<s>{t.title}</s>** ({t.task_id}) &bull; Completed at {t.completed_at.strftime('%Y-%m-%d %H:%M UTC') if t.completed_at else 'Archived'}")
            with col2:
                if st.button("↺ Reopen", key=f"reopen_{t.task_id}"):
                    repo.reopen_task(t.task_id)
                    scheduler.rebuild_heap()
                    st.rerun()
    else:
        st.info("No completed tasks yet.")

# ----------------- SETTINGS & DEMO -----------------
elif menu == "Settings & Demo":
    st.title("Settings & Demonstration")
    current_p = scheduler.policy.value
    new_policy = st.radio(
        "Active Scheduling Policy",
        [SchedulingPolicy.EARLIEST_DEADLINE.value, SchedulingPolicy.PRIORITY_FIRST.value],
        index=0 if current_p == SchedulingPolicy.EARLIEST_DEADLINE.value else 1,
        format_func=lambda x: "Earliest Deadline First (EDF) [Default Assessed]" if x == SchedulingPolicy.EARLIEST_DEADLINE.value else "Priority First (Hierarchy)"
    )
    if new_policy != current_p:
        scheduler.policy = SchedulingPolicy(new_policy)
        st.success(f"Policy updated to {new_policy}. Heap rebuilt in O(n).")
        st.rerun()

    st.markdown("---")
    st.markdown("### Demonstration Controls")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Reset to Academic Demo Dataset", type="primary"):
            repo.seed_demo_data(force=True)
            scheduler.rebuild_heap()
            st.success("Seeded academic demo tasks!")
            st.rerun()
    with c2:
        if st.button("Clear All Tasks"):
            repo.reset_all()
            scheduler.rebuild_heap()
            st.warning("Cleared database.")
            st.rerun()
