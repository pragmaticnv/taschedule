# TICKLINE: Viva & Demonstration Walkthrough Script
## Advanced Data Structures Mini-Project (Project 17)

This script is designed for a 5-to-10 minute project presentation or viva demonstration before the instructor or examination panel.

---

### Step 1: System Launch & Architecture Overview (1 Minute)

1. **Launch the Application**:
   ```bash
   python app.py
   ```
2. **Open the browser**: Navigate to `http://127.0.0.1:8000`.
3. **Talking Points**:
   > *"Good morning/afternoon. Today I am presenting Project 17: Task Scheduler with Deadlines, implemented in our project TICKLINE. 
   > Rather than using a generic database or relying on a black-box priority queue library, TICKLINE implements an explicit 0-indexed Binary Min-Heap from first principles. 
   > Notice our interface metaphor: it is crafted as a quiet, information-dense desktop instrument blending a studio control panel and an editorial timetable."*

---

### Step 2: Workbench & The "Next Up" Decision (2 Minutes)

1. Point to the **Top Diagnostic Strip**:
   > *"The top strip confirms our active policy: Earliest Deadline First (EDF), our UTC reference clock, and real-time status of the binary heap invariant."*
2. Point to the **NEXT UP Spotlight Card**:
   > *"At the center of our Workbench is the 'Next Up' card. This is not an arbitrary list item; it is the exact root element A[0] of our binary min-heap, retrieved in O(1) time."*
3. Expand and explain the **"Why This Task First?" Card**:
   > *"Notice the explanation card directly beneath it. The system transparently breaks down why this task sits at the root:
   > 1. Primary rule: Earliest deadline among active tasks.
   > 2. Tie-breaking: If two tasks share the same deadline, the tie is broken by Priority descending (-priority), then creation timestamp (FIFO), and finally stable task ID.
   > 3. It also names the runner-up contender that was outranked."*
4. Point to the **Deadline Pressure Rail**:
   > *"Above the Next Up card is our horizontal Deadline Pressure Rail, displaying immediate time pressure across all upcoming tasks."*
5. Point to the **Capacity Warning**:
   > *"Notice our Capacity Warning banner. It compares the sum of estimated task durations against our defined focus window (180 minutes). Crucially, the system explicitly disclaims that this is a single-threaded capacity estimate, not an unproven global optimal schedule."*

---

### Step 3: Heap Laboratory Deep Dive (3 Minutes) — *The Signature Moment*

1. Click on **Heap Laboratory** in the left navigation rail (`/heap-lab`).
2. Show the **Invariant Status Card**:
   > *"This is our Heap Laboratory. At the top, the system verifies that the min-heap invariant holds across all n elements: for every node i > 0, Key(Parent(i)) <= Key(i)."*
3. Walk through the **Sequential Array Representation**:
   > *"Here is the underlying physical array buffer A[0 .. n-1]. 
   > Index [0] in vermilion is our root. Each cell displays its array index, tree level, composite key, parent pointer, and child pointers. 
   > For instance, for node at index 1:
   > - Parent is (1 - 1) // 2 = 0
   > - Left child is 2*1 + 1 = 3
   > - Right child is 2*1 + 2 = 4
   > Notice there are no memory pointers stored here; the entire binary tree hierarchy is computed via pure index arithmetic."*
4. Inspect the **Parent-Child Mapping Table**:
   > *"This table proves the mathematical relationship for every single node in the tree."*
5. Review the **Operational Event Trace Log**:
   > *"Beneath the table is our live audit log. Every time an insertion, extraction, or rebuild occurs, this log records the exact number of comparisons and swaps performed during sift-up and sift-down."*

---

### Step 4: Dynamic Operations Demonstration (2 Minutes)

#### A. Task Completion (Extract-Min)
1. Navigate back to **Workbench / Queue**.
2. Click **"✓ Complete Next Up"**.
3. **Observe**:
   - The root task is popped in $\mathcal{O}(\log n)$ time.
   - A **Completion Receipt** appears with exact timestamp and updated queue state.
   - The previous root is archived in the **Completed Archive**, and the new root element immediately takes its place.

#### B. Inserting a High-Urgency Task (Sift-Up)
1. Click **+ Quick Capture** (`/tasks/new`).
2. Enter a task with an immediate deadline:
   - **Title**: `Urgent OS Bug Fix`
   - **Deadline**: Set to 1 hour from now.
   - **Priority**: `5 - Critical Urgency`
   - **Effort**: `30`
3. Click **Insert Into Heap Priority Queue**.
4. **Observe**:
   - The new task is inserted and immediately bubbles up to the root ($A[0]$).
   - In **Heap Laboratory**, the trace log shows the `INSERT` operation with comparison count and swaps.

---

### Step 5: Policy Re-Configuration & Rebuild (1 Minute)

1. Navigate to **Settings & Demo** (`/settings`).
2. Switch the policy from **Earliest Deadline First (EDF)** to **Priority First (Hierarchy)**.
3. Click **Save Configuration & Rebuild Heap**.
4. **Observe**:
   - The scheduler runs Floyd's bottom-up heapify in $\mathcal{O}(n)$ time.
   - The queue order dynamically rearranges to put Priority 5 tasks first, regardless of deadlines.
   - Switch back to **Earliest Deadline First** to restore the default academic policy.

---

### Step 6: Test Suite Verification & Conclusion (1 Minute)

1. Open the terminal and run:
   ```bash
   python -m pytest
   ```
2. **Observe**: All 23 tests pass cleanly in under 1 second.
3. **Closing Statement**:
   > *"To conclude: TICKLINE satisfies all course requirements for Project 17. It couples a mathematically sound, custom Binary Min-Heap Priority Queue with full persistence, transparent decision explanations, and a crafted desktop instrument interface. I am now ready for questions."*

---

### Viva Anticipated Questions & Model Answers

**Q1: Why did you choose a Binary Heap instead of an AVL Tree?**
> *Answer:* An AVL tree maintains full total ordering and requires three pointers per node plus balancing flags, resulting in high memory overhead and cache misses. A priority queue only requires accessing the minimum element ($A[0]$), which a binary heap achieves in $\mathcal{O}(1)$ time with zero pointer overhead in a contiguous array. Furthermore, building a heap takes strictly $\mathcal{O}(n)$ time, whereas constructing an AVL tree takes $\mathcal{O}(n \log n)$.

**Q2: How does bottom-up heapify achieve $\mathcal{O}(n)$ time when sift-down takes $\mathcal{O}(\log n)$?**
> *Answer:* Most nodes in a complete binary tree reside near the bottom. Half the nodes are leaves ($h=0$), requiring 0 swaps. Only one node (the root) is at maximum height. The sum of node heights converges to $\sum_{h=0}^\infty \frac{h}{2^h} = 2$, bounding the total operations strictly to $2cn = \mathcal{O}(n)$.

**Q3: How do you handle tie-breaks deterministically?**
> *Answer:* Each heap item is wrapped with a 4-tuple composite key: `(deadline, -priority, created_at, task_id)`. Python compares tuples lexicographically from left to right. Because `task_id` is unique and stable, ties are broken deterministically with zero ambiguity.

