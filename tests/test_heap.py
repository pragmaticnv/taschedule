"""
Unit tests for MinHeap and Priority Queue invariant enforcement.
"""
import pytest
import random
from core.priority_queue import MinHeap, HeapEntry


def test_empty_heap():
    heap = MinHeap[int, str]()
    assert heap.size() == 0
    assert heap.is_empty() is True
    assert heap.peek() is None
    assert heap.pop() is None


def test_single_element():
    heap = MinHeap[int, str]()
    heap.insert("Alpha", key=10)
    assert heap.size() == 1
    assert heap.is_empty() is False
    assert heap.peek() == "Alpha"

    val = heap.pop()
    assert val == "Alpha"
    assert heap.size() == 0
    assert heap.is_empty() is True


def test_min_heap_invariant_on_inserts():
    heap = MinHeap[int, int]()
    numbers = [42, 17, 89, 5, 23, 1, 99, 12, 55, 3]
    for num in numbers:
        heap.insert(num, key=num)
        valid, err = heap.verify_heap_invariant()
        assert valid, f"Invariant broken after inserting {num}: {err}"

    # Extract all, should yield sorted ascending order
    extracted = []
    while not heap.is_empty():
        extracted.append(heap.pop())
        valid, err = heap.verify_heap_invariant()
        assert valid, f"Invariant broken after popping: {err}"

    assert extracted == sorted(numbers)


def test_bottom_up_heapify_linear_time():
    heap = MinHeap[int, int]()
    random.seed(42)
    raw_data = [(x, x) for x in random.sample(range(1, 1000), 50)]

    heap.build_heap(raw_data, explanation_label="Random 50 items")
    valid, err = heap.verify_heap_invariant()
    assert valid, f"Heapify violated invariant: {err}"

    # Verify that popping everything produces strictly sorted output
    sorted_items = []
    while not heap.is_empty():
        sorted_items.append(heap.pop())

    assert sorted_items == sorted([x for x, _ in raw_data])


def test_composite_key_tie_breaking():
    heap = MinHeap[tuple, str]()
    # Composite key: (deadline_hour, -priority, id)
    # Task A: (10, -5, "TSK-1") -> deadline 10, prio 5
    # Task B: (10, -4, "TSK-2") -> deadline 10, prio 4
    # Task C: (8,  -1, "TSK-3") -> deadline 8, prio 1
    heap.insert("Task A", key=(10, -5, "TSK-1"))
    heap.insert("Task B", key=(10, -4, "TSK-2"))
    heap.insert("Task C", key=(8, -1, "TSK-3"))

    # First out should be Task C (earliest deadline 8)
    assert heap.pop() == "Task C"
    # Second out should be Task A (deadline 10, prio 5 beats prio 4)
    assert heap.pop() == "Task A"
    # Third out should be Task B
    assert heap.pop() == "Task B"


def test_parent_child_indexing():
    assert MinHeap.parent_index(1) == 0
    assert MinHeap.parent_index(2) == 0
    assert MinHeap.parent_index(3) == 1
    assert MinHeap.parent_index(4) == 1
    assert MinHeap.parent_index(5) == 2
    assert MinHeap.parent_index(6) == 2

    assert MinHeap.left_child_index(0) == 1
    assert MinHeap.right_child_index(0) == 2
    assert MinHeap.left_child_index(1) == 3
    assert MinHeap.right_child_index(1) == 4


def test_array_representation_and_trace():
    heap = MinHeap[int, str]()
    heap.insert("Root", key=10, label="Root item")
    heap.insert("Child1", key=20, label="Child 1")
    heap.insert("Child2", key=30, label="Child 2")

    repr_nodes = heap.get_array_representation()
    assert len(repr_nodes) == 3
    assert repr_nodes[0]["is_root"] is True
    assert repr_nodes[0]["parent_index"] is None
    assert repr_nodes[0]["left_child_index"] == 1
    assert repr_nodes[0]["right_child_index"] == 2

    trace = heap.get_trace_log()
    assert len(trace) >= 3
    assert trace[0].operation == "INSERT"

