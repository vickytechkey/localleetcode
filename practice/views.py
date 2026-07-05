from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
import json
import datetime
from practice.models import Problem, TestCase, Submission, DailyActivity, Goal
from practice.engine.runner import run_solution

def dashboard(request):
    # Calculations for streak
    today = datetime.date.today()
    
    # Solved problem IDs
    solved_problems_ids = Submission.objects.filter(status='PASS').values_list('problem_id', flat=True).distinct()
    solved_count = len(solved_problems_ids)
    total_problems = Problem.objects.count()
    
    # Attempts
    total_submissions = Submission.objects.count()
    success_rate = round((solved_count / total_submissions * 100), 1) if total_submissions > 0 else 0.0
    
    # Calculate streak
    activities = DailyActivity.objects.filter(solved__gt=0).order_by('-date')
    current_streak = 0
    longest_streak = 0
    
    if activities.exists():
        dates = [act.date for act in activities]
        yesterday = today - datetime.timedelta(days=1)
        
        # Current Streak
        if dates[0] == today or dates[0] == yesterday:
            current_streak = 1
            for i in range(1, len(dates)):
                if (dates[i-1] - dates[i]).days == 1:
                    current_streak += 1
                elif (dates[i-1] - dates[i]).days == 0:
                    continue
                else:
                    break
        
        # Longest Streak
        temp_streak = 1
        longest_streak = 1
        unique_dates = sorted(list(set(dates)), reverse=True)
        for i in range(1, len(unique_dates)):
            if (unique_dates[i-1] - unique_dates[i]).days == 1:
                temp_streak += 1
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
            else:
                temp_streak = 1
    
    # Heatmap data for last 365 days
    start_date = today - datetime.timedelta(days=365)
    activities_all = DailyActivity.objects.filter(date__gte=start_date)
    activity_map = {act.date.strftime("%Y-%m-%d"): {"attempts": act.attempts, "solved": act.solved} for act in activities_all}
    
    # Goals
    active_goals = Goal.objects.all()
    
    # Category statistics
    category_stats = []
    categories = Problem.objects.values_list('category', flat=True).distinct()
    for cat in categories:
        cat_total = Problem.objects.filter(category=cat).count()
        cat_solved = Problem.objects.filter(category=cat, id__in=solved_problems_ids).count()
        progress_pct = round((cat_solved / cat_total * 100), 1) if cat_total > 0 else 0
        category_stats.append({
            "name": cat,
            "solved": cat_solved,
            "total": cat_total,
            "progress_pct": progress_pct
        })
        
    context = {
        "solved_count": solved_count,
        "total_problems": total_problems,
        "total_submissions": total_submissions,
        "success_rate": success_rate,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "activity_map_json": json.dumps(activity_map),
        "active_goals": active_goals,
        "category_stats": category_stats
    }
    return render(request, "dashboard.html", context)

def problems_bank(request):
    query = request.GET.get('q', '')
    difficulty = request.GET.get('difficulty', '')
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    problems = Problem.objects.all()
    
    if query:
        problems = problems.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(concepts__icontains=query))
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if category:
        problems = problems.filter(category=category)
        
    # Get completed problems for the user
    solved_ids = set(Submission.objects.filter(status='PASS').values_list('problem_id', flat=True).distinct())
    attempted_ids = set(Submission.objects.values_list('problem_id', flat=True).distinct())
    
    filtered_problems = []
    for p in problems:
        is_solved = p.id in solved_ids
        is_attempted = p.id in attempted_ids
        
        p_status = "Completed" if is_solved else ("Attempted" if is_attempted else "Pending")
        
        if status == "Completed" and not is_solved:
            continue
        if status == "Pending" and is_solved:
            continue
        if status == "Attempted" and (is_solved or not is_attempted):
            continue
            
        p.status_label = p_status
        filtered_problems.append(p)
        
    categories = Problem.objects.values_list('category', flat=True).distinct()
    
    context = {
        "problems": filtered_problems,
        "categories": categories,
        "query": query,
        "selected_difficulty": difficulty,
        "selected_category": category,
        "selected_status": status
    }
    return render(request, "problems.html", context)

def practice_sandbox(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    submissions = Submission.objects.filter(problem=problem).order_by('-timestamp')
    
    # Default code template
    default_code = f"class Solution:\n    def {problem.function_name}(self):\n        pass\n"
    if problem.input_types:
        try:
            types = json.loads(problem.input_types)
            args_str = ", ".join([f"arg{i+1}" for i in range(len(types))])
            default_code = f"def {problem.function_name}({args_str}):\n    # Write your solution here\n    return None\n"
        except Exception:
            pass
            
    # Load last submission code if exists
    if submissions.exists():
        default_code = submissions.first().code
        
    context = {
        "problem": problem,
        "submissions": submissions,
        "default_code": default_code
    }
    return render(request, "practice.html", context)

@csrf_exempt
def run_code(request, problem_id):
    if request.method != "POST":
        return JsonResponse({"status": "ERROR", "message": "POST method required."})
    try:
        body = json.loads(request.body)
        code = body.get("code", "")
        problem = get_object_or_404(Problem, id=problem_id)
        result = run_solution(problem, code)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"status": "ERROR", "message": str(e)})

@csrf_exempt
def submit_code(request, problem_id):
    if request.method != "POST":
        return JsonResponse({"status": "ERROR", "message": "POST method required."})
    try:
        body = json.loads(request.body)
        code = body.get("code", "")
        problem = get_object_or_404(Problem, id=problem_id)
        result = run_solution(problem, code)
        
        # Save submission
        status = result.get("status", "FAIL")
        duration = result.get("total_time_ms", 0)
        err_msg = None
        if status != "PASS":
            err_msg = "\n".join([r.get("message", "") for r in result.get("results", []) if not r.get("passed")])
            
        Submission.objects.create(
            problem=problem,
            code=code,
            status=status,
            execution_time_ms=duration,
            error_message=err_msg
        )
        
        # Update daily activity
        today = datetime.date.today()
        activity, created = DailyActivity.objects.get_or_create(date=today)
        activity.attempts += 1
        if status == "PASS":
            # Check if this is the first PASS for this problem today
            # (to increment solved only for unique problems solved today)
            already_solved_today = Submission.objects.filter(
                problem=problem, 
                status='PASS', 
                timestamp__date=today
            ).count()
            if already_solved_today <= 1: # Counting the one we just created
                activity.solved += 1
        activity.save()
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"status": "ERROR", "message": str(e)})

def roadmap(request):
    solved_problems_ids = set(Submission.objects.filter(status='PASS').values_list('problem_id', flat=True).distinct())
    
    categories = [
        "Arrays & Hashing", "Two Pointers", "Sliding Window", "Stack & Queue",
        "Binary Search", "Linked List", "Trees & BST", "Heap / Priority Queue",
        "Backtracking", "Graphs & BFS/DFS", "Greedy", "Dynamic Programming", "Advanced Patterns"
    ]
    
    roadmap_data = []
    for cat in categories:
        probs = Problem.objects.filter(category=cat)
        if not probs.exists():
            continue
        
        total = probs.count()
        solved = probs.filter(id__in=solved_problems_ids).count()
        progress_pct = round((solved / total * 100), 1) if total > 0 else 0
        
        for p in probs:
            p.is_solved = p.id in solved_problems_ids
            
        roadmap_data.append({
            "category": cat,
            "solved": solved,
            "total": total,
            "progress_pct": progress_pct,
            "problems": probs
        })
        
    context = {
        "roadmap": roadmap_data
    }
    return render(request, "roadmap.html", context)

def help_page(request):
    return render(request, "help.html")
