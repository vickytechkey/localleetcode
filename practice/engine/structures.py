import collections

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def list_to_linked_list(arr):
    if not arr:
        return None
    dummy = ListNode(0)
    curr = dummy
    for val in arr:
        curr.next = ListNode(val)
        curr = curr.next
    return dummy.next

def linked_list_to_list(head):
    res = []
    curr = head
    visited = set()  # Prevent infinite loops in case of cycles
    while curr:
        if id(curr) in visited:
            break
        visited.add(id(curr))
        res.append(curr.val)
        curr = curr.next
    return res

def list_to_binary_tree(arr):
    if not arr:
        return None
    
    # Handle possible null/None strings or None types
    # e.g., [1, None, 2, 3]
    root = TreeNode(arr[0])
    queue = collections.deque([root])
    i = 1
    while queue and i < len(arr):
        curr = queue.popleft()
        
        # Left child
        if i < len(arr):
            if arr[i] is not None:
                curr.left = TreeNode(arr[i])
                queue.append(curr.left)
            i += 1
            
        # Right child
        if i < len(arr):
            if arr[i] is not None:
                curr.right = TreeNode(arr[i])
                queue.append(curr.right)
            i += 1
            
    return root

def binary_tree_to_list(root):
    if not root:
        return []
    res = []
    queue = collections.deque([root])
    while queue:
        node = queue.popleft()
        if node:
            res.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            res.append(None)
            
    # Trim trailing Nones
    while res and res[-1] is None:
        res.pop()
    return res
