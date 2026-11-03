"""
Custom Binary Min-Heap and Priority Queue Implementation.
Designed for educational transparency, algorithmic rigor, and live inspection.
"""
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timezone

T = TypeVar("T")
K = TypeVar("K")


@dataclass(order=True)
class HeapEntry(Generic[K, T]):
    """
    Heap entry containing an orderable composite key and associated value.
    The comparison is strictly delegated to the key.
    """
    key: K
    value: T = field(compare=False)


@dataclass
class HeapTraceEvent:
    """Record of an algorithmic operation for viva / Heap Lab inspection."""
    operation: str
    timestamp: str
    comparisons: int
    swaps: List[Tuple[int, int]]
    item_key: Optional[str] = None
    item_label: Optional[str] = None
    heap_size_before: int = 0
    heap_size_after: int = 0
    explanation: str = ""


class MinHeap(Generic[K, T]):
    """
    0-indexed Binary Min-Heap.
    
    Properties:
      - Array representation: A[0..n-1]
      - Root at index 0
      - For node at index i:
          Parent(i)      = (i - 1) // 2   (for i > 0)
          LeftChild(i)   = 2 * i + 1
          RightChild(i)  = 2 * i + 2
      - Min-Heap Invariant: For all i > 0, key(A[Parent(i)]) <= key(A[i])
    """

    def __init__(self, key_fn: Optional[Callable[[T], K]] = None):
        self._heap: List[HeapEntry[K, T]] = []
        self._key_fn: Optional[Callable[[T], K]] = key_fn
        self._trace_log: List[HeapTraceEvent] = []
        self._max_trace_len: int = 25
        self._total_comparisons: int = 0
        self._total_swaps: int = 0

    @staticmethod
    def parent_index(i: int) -> int:
        return (i - 1) // 2

    @staticmethod
    def left_child_index(i: int) -> int:
        return 2 * i + 1

    @staticmethod
    def right_child_index(i: int) -> int:
        return 2 * i + 2

    def size(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def peek(self) -> Optional[T]:
        """
        Inspect root element without removing it.
        Time Complexity: O(1)
        """
        if self.is_empty():
            return None
        return self._heap[0].value

    def peek_entry(self) -> Optional[HeapEntry[K, T]]:
        if self.is_empty():
            return None
        return self._heap[0]

    def insert(self, value: T, key: Optional[K] = None, label: str = "") -> None:
        """
        Insert an element into the min-heap.
        Appends to the end and sifts up.
        Time Complexity: O(log n)
        """
        if key is None:
            if self._key_fn is None:
                raise ValueError("Must provide a key or initialize heap with key_fn.")
            key = self._key_fn(value)

        entry = HeapEntry(key=key, value=value)
        size_before = len(self._heap)
        self._heap.append(entry)

        # Trace bookkeeping
        swaps: List[Tuple[int, int]] = []
        comparisons = self._sift_up(len(self._heap) - 1, swaps)
        self._total_comparisons += comparisons
        self._total_swaps += len(swaps)

        self._record_trace(
            operation="INSERT",
            comparisons=comparisons,
            swaps=swaps,
            item_key=str(key),
            item_label=label or str(value),
            heap_size_before=size_before,
            heap_size_after=len(self._heap),
            explanation=f"Inserted element at index {size_before}, sifted up with {len(swaps)} swap(s)."
        )

    def pop(self) -> Optional[T]:
        """
        Extract the minimum element (root) from the min-heap.
        Replaces root with the last element and sifts down.
        Time Complexity: O(log n)
        """
        if self.is_empty():
            return None

        size_before = len(self._heap)
        min_entry = self._heap[0]

        if len(self._heap) == 1:
            self._heap.pop()
            self._record_trace(
                operation="EXTRACT_MIN",
                comparisons=0,
                swaps=[],
                item_key=str(min_entry.key),
                item_label=str(min_entry.value),
                heap_size_before=size_before,
                heap_size_after=0,
                explanation="Popped sole element directly from root."
            )
            return min_entry.value

        # Move the last element to the root
        last_entry = self._heap.pop()
        self._heap[0] = last_entry

        swaps: List[Tuple[int, int]] = []
        comparisons = self._sift_down(0, swaps)
        self._total_comparisons += comparisons
        self._total_swaps += len(swaps)

        self._record_trace(
            operation="EXTRACT_MIN",
            comparisons=comparisons,
            swaps=swaps,
            item_key=str(min_entry.key),
            item_label=str(min_entry.value),
            heap_size_before=size_before,
            heap_size_after=len(self._heap),
            explanation=f"Extracted minimum. Replaced root with last element and sifted down with {len(swaps)} swap(s)."
        )

        return min_entry.value

    def build_heap(self, items: List[Tuple[K, T]], explanation_label: str = "Batch build") -> None:
        """
        Construct heap from an unsorted collection using bottom-up heapify.
        Starts at the deepest non-leaf parent: ((n - 2) // 2) down to 0.
        Time Complexity: O(n) - strict mathematical proof via sum(h / 2^h).
        """
        size_before = len(self._heap)
        self._heap = [HeapEntry(key=k, value=v) for k, v in items]
        n = len(self._heap)

        total_comp = 0
        all_swaps: List[Tuple[int, int]] = []

        start_idx = (n - 2) // 2
        for i in range(start_idx, -1, -1):
            swaps: List[Tuple[int, int]] = []
            comp = self._sift_down(i, swaps)
            total_comp += comp
            all_swaps.extend(swaps)

        self._total_comparisons += total_comp
        self._total_swaps += len(all_swaps)

        self._record_trace(
            operation="BUILD_HEAP",
            comparisons=total_comp,
            swaps=all_swaps,
            item_key=None,
            item_label=explanation_label,
            heap_size_before=size_before,
            heap_size_after=n,
            explanation=f"Built heap from {n} elements using bottom-up heapify in O(n) time. {len(all_swaps)} total swap(s)."
        )

    def _sift_up(self, index: int, swaps: List[Tuple[int, int]]) -> int:
        """
        Bubble element at index up until min-heap property is satisfied.
        Returns number of comparisons made.
        """
        comparisons = 0
        curr = index
        while curr > 0:
            parent = self.parent_index(curr)
            comparisons += 1
            if self._heap[curr].key < self._heap[parent].key:
                # Swap child and parent
                self._heap[curr], self._heap[parent] = self._heap[parent], self._heap[curr]
                swaps.append((curr, parent))
                curr = parent
            else:
                break
        return comparisons

    def _sift_down(self, index: int, swaps: List[Tuple[int, int]]) -> int:
        """
        Bubble element at index down until min-heap property is satisfied.
        Returns number of comparisons made.
        """
        comparisons = 0
        n = len(self._heap)
        curr = index

        while True:
            left = self.left_child_index(curr)
            right = self.right_child_index(curr)
            smallest = curr

            if left < n:
                comparisons += 1
                if self._heap[left].key < self._heap[smallest].key:
                    smallest = left

            if right < n:
                comparisons += 1
                if self._heap[right].key < self._heap[smallest].key:
                    smallest = right

            if smallest != curr:
                self._heap[curr], self._heap[smallest] = self._heap[smallest], self._heap[curr]
                swaps.append((curr, smallest))
                curr = smallest
            else:
                break

        return comparisons

    def verify_heap_invariant(self) -> Tuple[bool, Optional[str]]:
        """
        Mathematically checks that the min-heap invariant holds for all nodes.
        Returns (True, None) if valid, or (False, error_description) if broken.
        """
        n = len(self._heap)
        for i in range(n):
            left = self.left_child_index(i)
            right = self.right_child_index(i)

            if left < n and self._heap[left].key < self._heap[i].key:
                return False, f"Invariant violated at index {i} and left child {left}: parent key {self._heap[i].key} > child key {self._heap[left].key}"

            if right < n and self._heap[right].key < self._heap[i].key:
                return False, f"Invariant violated at index {i} and right child {right}: parent key {self._heap[i].key} > child key {self._heap[right].key}"

        return True, None

    def get_array_representation(self) -> List[Dict[str, Any]]:
        """
        Provides detailed structural metadata for each node in the heap array
        for rendering the Heap Lab visualizer.
        """
        nodes = []
        n = len(self._heap)
        for i, entry in enumerate(self._heap):
            parent_idx = self.parent_index(i) if i > 0 else None
            left_idx = self.left_child_index(i) if self.left_child_index(i) < n else None
            right_idx = self.right_child_index(i) if self.right_child_index(i) < n else None

            # Tree level: floor(log2(i + 1))
            level = 0
            temp = i + 1
            while temp > 1:
                temp //= 2
                level += 1

            nodes.append({
                "index": i,
                "key": entry.key,
                "value": entry.value,
                "parent_index": parent_idx,
                "left_child_index": left_idx,
                "right_child_index": right_idx,
                "level": level,
                "is_root": (i == 0),
                "is_leaf": (left_idx is None and right_idx is None),
            })
        return nodes

    def get_sorted_projection(self) -> List[T]:
        """
        Returns a sorted projection without mutating the original heap.
        Creates a shallow copy and repeatedly extracts min in O(n log n).
        """
        copy_heap = MinHeap[K, T]()
        copy_heap._heap = list(self._heap)
        sorted_items: List[T] = []
        while not copy_heap.is_empty():
            val = copy_heap.pop()
            if val is not None:
                sorted_items.append(val)
        return sorted_items

    def _record_trace(
        self,
        operation: str,
        comparisons: int,
        swaps: List[Tuple[int, int]],
        item_key: Optional[str],
        item_label: Optional[str],
        heap_size_before: int,
        heap_size_after: int,
        explanation: str,
    ) -> None:
        event = HeapTraceEvent(
            operation=operation,
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
            comparisons=comparisons,
            swaps=swaps,
            item_key=item_key,
            item_label=item_label,
            heap_size_before=heap_size_before,
            heap_size_after=heap_size_after,
            explanation=explanation,
        )
        self._trace_log.append(event)
        if len(self._trace_log) > self._max_trace_len:
            self._trace_log.pop(0)

    def get_trace_log(self) -> List[HeapTraceEvent]:
        return list(reversed(self._trace_log))

    def clear(self) -> None:
        self._heap.clear()

