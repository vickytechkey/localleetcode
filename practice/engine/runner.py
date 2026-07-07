import time
import json
import traceback
import sys
import copy
import io
from contextlib import redirect_stdout
from practice.engine.structures import (
    ListNode, TreeNode, list_to_linked_list, linked_list_to_list,
    list_to_binary_tree, binary_tree_to_list
)

class TimeoutException(Exception):
    pass

def execute_with_trace_and_timeout(func, args, timeout=2.0, max_steps=100):
    start_time = time.perf_counter()
    steps = []
    
    def tracer(frame, event, arg):
        if time.perf_counter() - start_time > timeout:
            raise TimeoutException("Time Limit Exceeded (Possible Infinite Loop)")
        
        # Enforce tracing of user function (ignore frame if it's external libraries like structures.py)
        if event in ('line', 'call') and len(steps) < max_steps:
            # Capture local variable states
            local_vars = {}
            for k, v in frame.f_locals.items():
                if not k.startswith('__') and not callable(v):
                    try:
                        # Avoid huge string representations for very large objects
                        v_str = str(v)
                        if len(v_str) > 100:
                            v_str = v_str[:97] + "..."
                        local_vars[k] = v_str
                    except Exception:
                        local_vars[k] = "<unserializable>"
            
            line_no = frame.f_lineno
            steps.append({
                "line": line_no,
                "event": event,
                "locals": local_vars
            })
        return tracer

    old_trace = sys.gettrace()
    sys.settrace(tracer)
    
    stdout_io = io.StringIO()
    exception = None
    actual_val = None
    duration_ms = 0
    tb_str = None
    
    try:
        t_start = time.perf_counter()
        with redirect_stdout(stdout_io):
            actual_val = func(*args)
        t_end = time.perf_counter()
        duration_ms = int((t_end - t_start) * 1000)
    except Exception as e:
        exception = e
        tb_str = traceback.format_exc()
    finally:
        sys.settrace(old_trace)
        
    captured_stdout = stdout_io.getvalue()
    
    return {
        "actual_val": actual_val,
        "duration_ms": duration_ms,
        "stdout": captured_stdout,
        "exception": exception,
        "traceback": tb_str,
        "steps": steps
    }

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
        namespace['ListNode'] = ListNode
        namespace['TreeNode'] = TreeNode
        
        exec(user_code, namespace)
        
        func_name = problem.function_name
        if func_name not in namespace or not callable(namespace[func_name]):
            return {
                "status": "ERROR",
                "message": f"Compilation Error: Could not find function '{func_name}' in your code."
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
    
    for idx, tc in enumerate(test_cases):
        try:
            raw_args = json.loads(tc.inputs)
            expected_val = json.loads(tc.expected_output)
            args = copy.deepcopy(raw_args)
            
            category = problem.category.lower()
            converted_args = []
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
            
            run_result = execute_with_trace_and_timeout(solve_func, converted_args, timeout=2.0)
            
            if run_result["exception"]:
                raise run_result["exception"]
                
            actual_val = run_result["actual_val"]
            duration_ms = run_result["duration_ms"]
            total_time_ms += duration_ms
            
            if isinstance(actual_val, ListNode):
                actual_serialized = linked_list_to_list(actual_val)
            elif isinstance(actual_val, TreeNode):
                actual_serialized = binary_tree_to_list(actual_val)
            elif actual_val is None and isinstance(expected_val, list):
                actual_serialized = []
            else:
                actual_serialized = actual_val
                
            passed = False
            comp_mode = tc.comparison_mode or 'Exact'
            
            if comp_mode == 'Ignore Order':
                if isinstance(actual_serialized, list) and isinstance(expected_val, list):
                    try:
                        passed = sorted(actual_serialized) == sorted(expected_val)
                    except TypeError:
                        passed = len(actual_serialized) == len(expected_val) and all(x in expected_val for x in actual_serialized)
                else:
                    passed = actual_serialized == expected_val
            else:
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
                "message": "Passed" if passed else "Mismatch",
                "stdout": run_result["stdout"],
                "steps": run_result["steps"]
            })
            
        except Exception as e:
            all_passed = False
            tb = run_result.get("traceback") if 'run_result' in locals() else traceback.format_exc()
            results.append({
                "test_case_id": tc.id,
                "passed": False,
                "duration_ms": 0,
                "inputs_preview": tc.inputs,
                "actual": None,
                "expected": tc.expected_output,
                "message": f"Runtime Error: {str(e)}",
                "traceback": tb,
                "stdout": run_result.get("stdout", "") if 'run_result' in locals() else "",
                "steps": run_result.get("steps", []) if 'run_result' in locals() else []
            })
            
    status = "PASS" if all_passed else "FAIL"
    return {
        "status": status,
        "results": results,
        "total_time_ms": total_time_ms
    }

def run_solution_stream(problem, user_code):
    """
    Executes the user's Python solution and yields progress updates for each test case.
    """
    test_cases = problem.test_cases.all()
    total = len(test_cases)
    if not test_cases:
        yield {"type": "error", "message": "No test cases found for this problem."}
        return
        
    # Compile the user's code
    namespace = {}
    try:
        namespace['ListNode'] = ListNode
        namespace['TreeNode'] = TreeNode
        exec(user_code, namespace)
        
        func_name = problem.function_name
        if func_name not in namespace or not callable(namespace[func_name]):
            yield {
                "type": "error",
                "message": f"Compilation Error: Could not find function '{func_name}' in your code."
            }
            return
        solve_func = namespace[func_name]
    except Exception as e:
        yield {
            "type": "error",
            "message": f"Compilation/Syntax Error: {str(e)}",
            "traceback": traceback.format_exc()
        }
        return
        
    results = []
    all_passed = True
    total_time_ms = 0
    
    for idx, tc in enumerate(test_cases):
        percentage = int((idx / total) * 100)
        
        try:
            inputs_preview = json.loads(tc.inputs)
        except Exception:
            inputs_preview = tc.inputs
            
        yield {
            "type": "progress",
            "index": idx + 1,
            "total": total,
            "percentage": percentage,
            "inputs_preview": inputs_preview
        }
        
        run_result = None
        try:
            raw_args = json.loads(tc.inputs)
            expected_val = json.loads(tc.expected_output)
            args = copy.deepcopy(raw_args)
            
            category = problem.category.lower()
            converted_args = []
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
            
            run_result = execute_with_trace_and_timeout(solve_func, converted_args, timeout=2.0)
            
            if run_result["exception"]:
                raise run_result["exception"]
                
            actual_val = run_result["actual_val"]
            duration_ms = run_result["duration_ms"]
            total_time_ms += duration_ms
            
            if isinstance(actual_val, ListNode):
                actual_serialized = linked_list_to_list(actual_val)
            elif isinstance(actual_val, TreeNode):
                actual_serialized = binary_tree_to_list(actual_val)
            elif actual_val is None and isinstance(expected_val, list):
                actual_serialized = []
            else:
                actual_serialized = actual_val
                
            passed = False
            comp_mode = tc.comparison_mode or 'Exact'
            
            if comp_mode == 'Ignore Order':
                if isinstance(actual_serialized, list) and isinstance(expected_val, list):
                    try:
                        passed = sorted(actual_serialized) == sorted(expected_val)
                    except TypeError:
                        passed = len(actual_serialized) == len(expected_val) and all(x in expected_val for x in actual_serialized)
                else:
                    passed = actual_serialized == expected_val
            else:
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
                "message": "Passed" if passed else "Mismatch",
                "stdout": run_result["stdout"],
                "steps": run_result["steps"]
            })
            
        except Exception as e:
            all_passed = False
            tb = run_result.get("traceback") if (run_result and run_result.get("traceback")) else traceback.format_exc()
            results.append({
                "test_case_id": tc.id,
                "passed": False,
                "duration_ms": 0,
                "inputs_preview": tc.inputs,
                "actual": None,
                "expected": tc.expected_output,
                "message": f"Runtime Error: {str(e)}",
                "traceback": tb,
                "stdout": run_result["stdout"] if (run_result and "stdout" in run_result) else "",
                "steps": run_result["steps"] if (run_result and "steps" in run_result) else []
            })
            
    # Yield final result
    yield {
        "type": "result",
        "status": "PASS" if all_passed else "FAIL",
        "results": results,
        "total_time_ms": total_time_ms
    }
