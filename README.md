# TICKLINE — Task Scheduler with Deadlines
### Advanced Data Structures Mini-Project | Project 17

[![Tests](https://img.shields.io/badge/pytest-23%20passed-brightgreen.svg)]()
[![Algorithm](https://img.shields.io/badge/Data%20Structure-Binary%20Min--Heap-orange.svg)]()
[![Design](https://img.shields.io/badge/UI-Crafted%20Instrument-lightgrey.svg)]()

> A deadline-aware scheduling workbench for students and engineers who want to see what deserves attention next, why it is next, and whether their available time is enough.

---

## 1. Quickstart & Launch Instructions

### Prerequisites
- Python 3.11+ or 3.12+
- SQLite3 (included with Python standard library)

### Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### Launch the Application (Crafted Instrument UI)
```bash
python app.py
```
Open your browser to: **`http://127.0.0.1:8000`**

*(Note: A Streamlit edition is also provided in `streamlit_app.py` for platforms supporting Streamlit: `streamlit run streamlit_app.py`)*

### Run Automated Test Suite
```bash
python -m pytest
```
Executes all 23 unit, invariant, scheduling, and route integration tests.

---

## 2. Core Features & Signatures

1. **Custom Binary Min-Heap Priority Queue (`core/priority_queue.py`)**:
   - Zero-indexed contiguous array implementation ($A[0 \dots n-1]$).
   - Parent and child links computed via exact index arithmetic without pointer overhead.
   - $\mathcal{O}(1)$ root inspection, $\mathcal{O}(\log n)$ insertion (sift-up) and extraction (sift-down).
   - Floyd's bottom-up heapify in strictly $\mathcal{O}(n)$ linear time.
2. **Deterministic Multi-Tier Ordering Policy (`core/scheduler.py`)**:
   - **Earliest Deadline First (EDF) [Default]**: Primary key = Deadline ascending; Tie-breaker 1 = Priority descending (`-priority`); Tie-breaker 2 = Creation timestamp (FIFO); Tie-breaker 3 = Stable task ID.
   - **Priority-First (Hierarchy)**: Switchable in Settings for examiners who require priority-first ordering.
3. **"Why This Task?" Algorithmic Proof Card**:
   - Explicitly cites the active comparator rule and breaks down why the root item ranks first compared to runner-up contenders.
4. **Deadline Pressure Rail**:
   - Chronological horizontal agenda strip showing immediate time pressure without color overload.
5. **Heuristic Capacity Estimation**:
   - Compares cumulative active task effort against the user's available focus window.
   - Honestly disclaims that this is a single-threaded capacity estimate, not an optimal scheduling proof.
6. **Heap Laboratory (`/heap-lab`)**:
   - **Array Visualizer**: Displays $A[0 \dots n-1]$ with indices, keys, and levels.
   - **Parent-Child Mapping**: Real-time tabular index verification ($\lfloor(i-1)/2\rfloor$, $2i+1$, $2i+2$).
   - **Live Event Trace Log**: Audit trail recording comparison counts and swap pairs for every heap operation.
   - **Invariant Checker**: Direct mathematical assertion of the min-heap condition.
7. **SQLite Persistence (`core/repository.py`)**:
   - Durable ACID storage in `data/tickline.db`.
   - Seed and reset utilities for predictable coursework demonstrations.

---

## 3. Project File Structure

```
ADSA PROJECT/
├── app.py                      # FastAPI web server & route controllers
├── streamlit_app.py            # Streamlit edition (sharing core modules)
├── requirements.txt            # Dependency definitions
├── pytest.ini                  # Pytest configuration
├── README.md                   # Project overview & documentation
│
├── core/                       # Core Algorithmic Engine
│   ├── __init__.py
│   ├── models.py               # Domain models (Task dataclass, validation)
│   ├── priority_queue.py       # Custom Binary Min-Heap, trace logger
│   ├── scheduler.py            # EDF & Priority policies, "Why this task?"
│   └── repository.py           # SQLite persistence & demo data seeder
│
├── static/                     # Crafted Instrument UI Styling
│   └── styles.css              # Editorial timetable & studio panel CSS
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Slim navigation rail & diagnostic strip
│   ├── queue.html              # Main Workbench (Next Up, Queue, Rail)
│   ├── all_tasks.html          # Full task inventory & filters
│   ├── task_form.html          # Quick capture & edit forms
│   ├── heap_lab.html           # Live Heap Laboratory & trace visualizer
│   ├── completed.html          # Historical archive of completed tasks
│   └── settings.html           # Policy switcher & demo controls
│
├── tests/                      # Automated Verification (23 Tests)
│   ├── __init__.py
│   ├── test_heap.py            # Invariant, sift-up/down, heapify tests
│   ├── test_scheduler.py       # Comparator policies, tie-breakers
│   ├── test_repository.py      # SQLite CRUD, model validation
│   └── test_api.py             # Route handling & REST endpoints
│
├── docs/                       # Academic Reports
│   ├── project_report.md       # Comprehensive academic submission report
│   └── demo_script.md          # Step-by-step viva presentation script
│
└── data/                       # Local database storage
    ├── .gitkeep
    └── tickline.db             # SQLite database file
```

---

## 4. Asymptotic Complexity Reference

| Operation | Time Complexity | Auxiliary Space | Asymptotic Justification |
| :--- | :---: | :---: | :--- |
| **Peek Root** | $\mathcal{O}(1)$ | $\mathcal{O}(1)$ | Array access at $A[0]$. |
| **Insert Task** | $\mathcal{O}(\log n)$ | $\mathcal{O}(1)$ | Appends to buffer, sifts up along tree height $\le \lfloor\log_2 n\rfloor$. |
| **Extract Min (Pop)** | $\mathcal{O}(\log n)$ | $\mathcal{O}(1)$ | Replaces root with last element, sifts down tree. |
| **Bottom-Up Heapify** | $\mathcal{O}(n)$ | $\mathcal{O}(1)$ | Sifts down non-leaves; sum of heights converges to $2n$. |
| **Sorted Projection** | $\mathcal{O}(n \log n)$ | $\mathcal{O}(n)$ | $n$ successive extractions from a shallow copy of the heap. |
| **Arbitrary Search** | $\mathcal{O}(n)$ | $\mathcal{O}(1)$ | Heap is partially ordered; lacks binary search property. |

---

## 5. Viva Talking Points

1. **Why a Min-Heap over an AVL Tree?**
   - An AVL tree requires 3 pointers per node plus balancing flags, incurring high pointer overhead and poor cache locality. A binary heap uses a flat contiguous array with zero pointer overhead. Constructing a heap takes $\mathcal{O}(n)$ time via bottom-up heapify, compared to $\mathcal{O}(n \log n)$ for an AVL tree.
2. **Why rebuild after edits?**
   - For an academic scheduler ($n < 50,000$), rebuilding via bottom-up heapify in $\mathcal{O}(n)$ is deterministic, simple, fast (fractions of a millisecond), and avoids stale pointers.
3. **What is the difference between Priority Queue ordering and an optimal schedule?**
   - A priority queue provides a greedy, deterministic ordering of eligible items. It does not solve the NP-hard constrained bin-packing or multi-resource job-shop scheduling problem.

