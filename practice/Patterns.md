# Master DSA Pattern Recognition Guide

To stop memorizing code and start recognizing solutions, you must train your brain to identify the underlying **Patterns**. This guide breaks down the core patterns seeded in this codebase, explaining how to spot them, their code templates, and which problems use them.

---

## 1. Sliding Window (Dynamic & Fixed)
*   **How to spot it**: 
    *   The problem asks for a contiguous subarray, substring, or sequence (e.g., "longest subarray", "minimum substring").
    *   The input is an array or string, and you need to optimize a subset of it meeting a condition.
*   **The Brain Hack**: Instead of scanning all possible subsets (which takes $O(N^2)$), you maintain two pointers (`left` and `right`) and slide the window. Expand `right` to include elements, and shrink `left` when constraints are violated.
*   **Python Template**:
    ```python
    def sliding_window(arr):
        left = 0
        state = initial_state()
        ans = 0
        for right in range(len(arr)):
            # Add right element to state
            update_state(state, arr[right])
            
            # Shrink window from left until constraint is satisfied
            while constraint_violated(state):
                remove_from_state(state, arr[left])
                left += 1
                
            ans = max(ans, right - left + 1)
        return ans
    ```
*   **Key Problems in Project**:
    *   [Best Time to Buy and Sell Stock](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=sliding-window)
    *   [Longest Substring Without Repeating Characters](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=sliding-window)
    *   [Minimum Window Substring](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=sliding-window)

---

## 2. Two Pointers
*   **How to spot it**:
    *   The input is sorted (or you can sort it), and you need to find a pair, triplet, or swap items in-place.
    *   You need to compare elements from two different boundaries (start vs. end) moving inward.
*   **The Brain Hack**: Start one pointer at index `0` and one at `len(arr) - 1`. Move them inward conditionally. This eliminates half of the search space at each step, optimizing $O(N^2)$ to $O(N)$.
*   **Python Template**:
    ```python
    def two_pointers(nums, target):
        left, right = 0, len(nums) - 1
        while left < right:
            current_sum = nums[left] + nums[right]
            if current_sum == target:
                return [left, right]
            elif current_sum < target:
                left += 1
            else:
                right -= 1
        return []
    ```
*   **Key Problems in Project**:
    *   [Two Sum II - Input Array Is Sorted](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=two-pointers)
    *   [3Sum](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=two-pointers)
    *   [Container With Most Water](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=two-pointers)

---

## 3. Monotonic Stack
*   **How to spot it**:
    *   The problem asks to find the "next greater element", "next smaller element", or "nearest warmer day" for every index.
    *   You need to compare a value against a history of preceding values and maintain sorting order.
*   **The Brain Hack**: Use a stack that stores elements (or their indices) in strictly increasing or decreasing order. As you scan the array, pop elements from the stack that are smaller than the current element.
*   **Python Template**:
    ```python
    def monotonic_stack(temperatures):
        ans = [0] * len(temperatures)
        stack = [] # Monotonic decreasing stack (stores indices)
        for i in range(len(temperatures)):
            while stack and temperatures[i] > temperatures[stack[-1]]:
                idx = stack.pop()
                ans[idx] = i - idx
            stack.append(i)
        return ans
    ```
*   **Key Problems in Project**:
    *   [Daily Temperatures](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=monotonic-stack)
    *   [Next Greater Element I](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=monotonic-stack)
    *   [Largest Rectangle in Histogram](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=monotonic-stack)

---

## 4. Binary Search on Answer
*   **How to spot it**:
    *   The problem asks for a minimum or maximum threshold value (e.g., "minimum capacity to ship in D days", "minimum speed to eat bananas").
    *   If you choose a random number $X$, it is easy to check if $X$ is valid/feasible, and if $X$ is valid, any number $> X$ is also valid (monotonicity).
*   **The Brain Hack**: Instead of testing every number sequentially from $1$ to $Max$, binary search the *answer range* itself. Check the midpoint; if feasible, try to find a smaller/better solution; if infeasible, narrow your search to the larger half.
*   **Python Template**:
    ```python
    def binary_search_on_answer(weights, d):
        def is_feasible(capacity):
            days, current_weight = 1, 0
            for w in weights:
                if current_weight + w > capacity:
                    days += 1
                    current_weight = 0
                current_weight += w
            return days <= d
            
        low, high = max(weights), sum(weights)
        ans = high
        while low <= high:
            mid = (low + high) // 2
            if is_feasible(mid):
                ans = mid
                high = mid - 1 # Try to find a smaller feasible capacity
            else:
                low = mid + 1  # Need a larger capacity
        return ans
    ```
*   **Key Problems in Project**:
    *   [Koko Eating Bananas](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=binary-search)
    *   [Capacity To Ship Packages Within D Days](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=binary-search)
    *   [Split Array Largest Sum](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=binary-search)

---

## 5. Breadth-First Search (BFS) / Shortest Path
*   **How to spot it**:
    *   Find the "shortest path", "minimum steps", or "nearest distance" in an unweighted grid, maze, or graph.
    *   Level-by-level traversal (e.g., print tree levels, virus spreading simulations).
*   **The Brain Hack**: Use a Queue. Process all neighbors at distance 1, then distance 2, etc. Visited nodes must be tracked in a set to prevent infinite loops.
*   **Python Template**:
    ```python
    from collections import deque

    def bfs(grid, start):
        queue = deque([(start[0], start[1], 0)]) # (row, col, distance)
        visited = {start}
        while queue:
            r, c, dist = queue.popleft()
            if grid[r][c] == "TARGET":
                return dist
            for nr, nc in get_neighbors(r, c):
                if (nr, nc) not in visited:
                    visited.add((nr, nc))
                    queue.append((nr, nc, dist + 1))
        return -1
    ```
*   **Key Problems in Project**:
    *   [Rotting Oranges](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=BFS)
    *   [Binary Tree Level Order Traversal](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=BFS)
    *   [Word Ladder](file:///home/vignesh/github/localleetcode/practice/problems.html?pattern=BFS)
