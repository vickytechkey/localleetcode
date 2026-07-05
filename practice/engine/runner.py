import time
import json
import traceback
import sys
import copy
from practice.engine.structures import (
    ListNode, TreeNode, list_to_linked_list, linked_list_to_list,
    list_to_binary_tree, binary_tree_to_list
)

def run_solution(problem, user_code):
    """
    Executes the user's Python solution against all test cases of the problem.
    """
    test_cases = problem.test_cases.all()
    if not test_cases:
        return {
            "status": "ERROR",
            "message": "No test cases found for this problem."
        }
        
    # Compile the user's code
    namespace = {}
    try:
        # Include custom classes in namespace so user can use them
        namespace['ListNode'] = ListNode
        namespace['TreeNode'] = TreeNode
        
        exec(user_code, namespace)
        
        func_name = problem.function_name
        if func_name not in namespace or not callable(namespace[func_name]):
            return {
                "status": "ERROR",
                "message": f"Compilation Error: Could not find function '{func_name}' in your code. Please make sure the function is defined exactly as requested."
            }
        solve_func = namespace[func_name]
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Compilation/Syntax Error: {str(e)}",
            "traceback": traceback.format_exc()
        }
        
    results = []
    all_passed = True
    total_time_ms = 0
    
    # Run test cases
    for idx, tc in enumerate(test_cases):
        try:
            # Parse inputs (a JSON array of arguments, e.g. [[2, 7, 11, 15], 9])
            raw_args = json.loads(tc.inputs)
            expected_val = json.loads(tc.expected_output)
            
            # Deep copy to ensure user mutations don't affect original test cases
            args = copy.deepcopy(raw_args)
            
            # Convert inputs based on category
            category = problem.category.lower()
            converted_args = []
            
            # Helper to check if a type needs conversion
            # We convert list inputs to ListNode or TreeNode if the category matches
            # Let's inspect input_types schema if it exists
            # We can define input_types as a JSON list, e.g. ["ListNode", "int"]
            try:
                type_hints = json.loads(problem.input_types)
            except Exception:
                type_hints = []
                
            for i, arg in enumerate(args):
                hint = type_hints[i] if i < len(type_hints) else ""
                if hint == "ListNode" and isinstance(arg, list):
                    converted_args.append(list_to_linked_list(arg))
                elif hint == "TreeNode" and isinstance(arg, list):
                    converted_args.append(list_to_binary_tree(arg))
                elif "linked list" in category and isinstance(arg, list) and (hint == "" or hint == "ListNode"):
                    converted_args.append(list_to_linked_list(arg))
                elif ("tree" in category or "bst" in category) and isinstance(arg, list) and (hint == "" or hint == "TreeNode"):
                    converted_args.append(list_to_binary_tree(arg))
                else:
                    converted_args.append(arg)
            
            # Run the user's function
            t_start = time.perf_counter()
            actual_val = solve_func(*converted_args)
            t_end = time.perf_counter()
            
            duration_ms = int((t_end - t_start) * 1000)
            total_time_ms += duration_ms
            
            # Convert actual output back to standard Python types for serialization and comparison
            if isinstance(actual_val, ListNode):
                actual_serialized = linked_list_to_list(actual_val)
            elif isinstance(actual_val, TreeNode):
                actual_serialized = binary_tree_to_list(actual_val)
            elif actual_val is None and isinstance(expected_val, list):
                actual_serialized = []
            else:
                actual_serialized = actual_val
                
            # Perform comparison
            passed = False
            comp_mode = tc.comparison_mode or 'Exact'
            
            if comp_mode == 'Ignore Order':
                if isinstance(actual_serialized, list) and isinstance(expected_val, list):
                    try:
                        passed = sorted(actual_serialized) == sorted(expected_val)
                    except TypeError:
                        # Fallback if un-sortable
                        passed = len(actual_serialized) == len(expected_val) and all(x in expected_val for x in actual_serialized)
                else:
                    passed = actual_serialized == expected_val
            else: # Exact
                passed = actual_serialized == expected_val
                
            if not passed:
                all_passed = False
                
            results.append({
                "test_case_id": tc.id,
                "passed": passed,
                "duration_ms": duration_ms,
                "inputs_preview": raw_args,
                "actual": actual_serialized,
                "expected": expected_val,
                "message": "Passed" if passed else "Mismatch"
            })
            
        except Exception as e:
            all_passed = False
            results.append({
                "test_case_id": tc.id,
                "passed": False,
                "duration_ms": 0,
                "inputs_preview": tc.inputs,
                "actual": None,
                "expected": tc.expected_output,
                "message": f"Runtime Error: {str(e)}",
                "traceback": traceback.format_exc()
            })
            
    status = "PASS" if all_passed else "FAIL"
    return {
        "status": status,
        "results": results,
        "total_time_ms": total_time_ms
    }
