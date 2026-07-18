from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q
from django.utils import timezone
import json
import datetime
from practice.models import Problem, TestCase, Submission, DailyActivity, Goal, RoadmapOptIn
from practice.engine.runner import run_solution, run_solution_stream

def dashboard(request):
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
    active_goals = Goal.objects.all().order_by('-created_at')
    
    # Category statistics (with Expert Score)
    category_stats = []
    categories = Problem.objects.values_list('category', flat=True).distinct()
    for cat in categories:
        cat_probs = Problem.objects.filter(category=cat)
        cat_total = cat_probs.count()
        cat_solved_qs = cat_probs.filter(id__in=solved_problems_ids)
        cat_solved = cat_solved_qs.count()
        progress_pct = round((cat_solved / cat_total * 100), 1) if cat_total > 0 else 0
        
        # Calculate Expert Score
        easy_total = cat_probs.filter(difficulty='Easy').count()
        medium_total = cat_probs.filter(difficulty='Medium').count()
        hard_total = cat_probs.filter(difficulty='Hard').count()
        
        easy_solved = cat_solved_qs.filter(difficulty='Easy').count()
        medium_solved = cat_solved_qs.filter(difficulty='Medium').count()
        hard_solved = cat_solved_qs.filter(difficulty='Hard').count()
        
        max_points = easy_total * 0.5 + medium_total * 1.0 + hard_total * 2.0
        solved_points = easy_solved * 0.5 + medium_solved * 1.0 + hard_solved * 2.0
        expert_score = min(100, round((solved_points / max_points * 100))) if max_points > 0 else 0
        
        category_stats.append({
            "name": cat,
            "solved": cat_solved,
            "total": cat_total,
            "progress_pct": progress_pct,
            "expert_score": expert_score
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
        "category_stats": category_stats,
        "all_categories": categories
    }
    return render(request, "dashboard.html", context)

@csrf_exempt
def create_goal(request):
    if request.method == "POST":
        goal_type = request.POST.get("type", "Daily")
        target = int(request.POST.get("target", 1))
        difficulty = request.POST.get("difficulty", "") or None
        category = request.POST.get("category", "") or None
        
        today = datetime.date.today()
        if goal_type == "Daily":
            start_date = today
            end_date = today
        elif goal_type == "Weekly":
            start_date = today
            end_date = today + datetime.timedelta(days=6)
        else: # Monthly
            start_date = today
            end_date = today + datetime.timedelta(days=30)
            
        Goal.objects.create(
            type=goal_type,
            target=target,
            start_date=start_date,
            end_date=end_date,
            difficulty=difficulty,
            category=category,
            created_at=timezone.now()
        )
    return redirect('practice:dashboard')

@csrf_exempt
def delete_goal(request, goal_id):
    if request.method == "POST":
        goal = get_object_or_404(Goal, id=goal_id)
        goal.delete()
    return redirect('practice:dashboard')

def problems_bank(request):
    query = request.GET.get('q', '')
    difficulty = request.GET.get('difficulty', '')
    category = request.GET.get('category', '')
    status = request.GET.get('status', '')
    milestone = request.GET.get('milestone', '')
    
    problems = Problem.objects.all()
    
    if query:
        problems = problems.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(concepts__icontains=query))
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    if category:
        problems = problems.filter(category=category)
    if milestone:
        try:
            problems = problems.filter(milestone=int(milestone))
        except ValueError:
            pass
        
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
        "selected_status": status,
        "selected_milestone": milestone
    }
    return render(request, "problems.html", context)


def practice_sandbox(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    submissions = Submission.objects.filter(problem=problem).order_by('-timestamp')
    
    default_code = f"class Solution:\n    def {problem.function_name}(self):\n        pass\n"
    if problem.input_types:
        try:
            types = json.loads(problem.input_types)
            args_str = ", ".join([f"arg{i+1}" for i in range(len(types))])
            default_code = f"def {problem.function_name}({args_str}):\n    # Write your solution here\n    return None\n"
        except Exception:
            pass
            
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
        
        def stream_generator():
            try:
                for update in run_solution_stream(problem, code):
                    yield json.dumps(update) + "\n"
            except GeneratorExit:
                pass
                
        return StreamingHttpResponse(stream_generator(), content_type="application/x-ndjson")
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
        
        def stream_generator():
            try:
                final_result = None
                for update in run_solution_stream(problem, code):
                    if update.get("type") == "result":
                        final_result = update
                    yield json.dumps(update) + "\n"
                
                if final_result:
                    status = final_result.get("status", "FAIL")
                    duration = final_result.get("total_time_ms", 0)
                    err_msg = None
                    if status != "PASS":
                        err_msg = "\n".join([r.get("message", "") for r in final_result.get("results", []) if not r.get("passed")])
                        
                    Submission.objects.create(
                        problem=problem,
                        code=code,
                        status=status,
                        execution_time_ms=duration,
                        error_message=err_msg
                    )
                    
                    today = datetime.date.today()
                    activity, created = DailyActivity.objects.get_or_create(date=today)
                    activity.attempts += 1
                    if status == "PASS":
                        already_solved_today = Submission.objects.filter(
                            problem=problem, 
                            status='PASS', 
                            timestamp__date=today
                        ).count()
                        if already_solved_today <= 1:
                            activity.solved += 1
                    activity.save()
            except GeneratorExit:
                pass
                
        return StreamingHttpResponse(stream_generator(), content_type="application/x-ndjson")
    except Exception as e:
        return JsonResponse({"status": "ERROR", "message": str(e)})

def roadmap(request):
    solved_problems_ids = set(Submission.objects.filter(status='PASS').values_list('problem_id', flat=True).distinct())
    
    # 5 structured levels
    levels_config = {
        "Beginner": ["Arrays", "Hashing", "Two Pointers", "Stack & Queue"],
        "Intermediate": ["Sliding Window", "Binary Search", "Linked List"],
        "Advanced": ["Trees & BST", "Heap / Priority Queue", "Backtracking"],
        "Expert": ["Graphs & BFS/DFS", "Greedy"],
        "Master": ["Dynamic Programming", "Advanced Patterns"]
    }
    
    roadmap_levels = []
    
    for lvl_name, categories in levels_config.items():
        is_opted_in = RoadmapOptIn.objects.filter(level_name=lvl_name).exists()
        lvl_total = 0
        lvl_solved = 0
        categories_data = []
        
        for cat in categories:
            probs = Problem.objects.filter(category=cat)
            total = probs.count()
            solved = probs.filter(id__in=solved_problems_ids).count()
            progress_pct = round((solved / total * 100), 1) if total > 0 else 0
            
            # Calculate Expert Score for this category
            easy_total = probs.filter(difficulty='Easy').count()
            medium_total = probs.filter(difficulty='Medium').count()
            hard_total = probs.filter(difficulty='Hard').count()
            
            easy_solved = probs.filter(difficulty='Easy', id__in=solved_problems_ids).count()
            medium_solved = probs.filter(difficulty='Medium', id__in=solved_problems_ids).count()
            hard_solved = probs.filter(difficulty='Hard', id__in=solved_problems_ids).count()
            
            max_points = easy_total * 0.5 + medium_total * 1.0 + hard_total * 2.0
            solved_points = easy_solved * 0.5 + medium_solved * 1.0 + hard_solved * 2.0
            expert_score = min(100, round((solved_points / max_points * 100))) if max_points > 0 else 0
            
            lvl_total += total
            lvl_solved += solved
            
            # Decorate problems with solved flag
            for p in probs:
                p.is_solved = p.id in solved_problems_ids
                
            categories_data.append({
                "category": cat,
                "solved": solved,
                "total": total,
                "progress_pct": progress_pct,
                "expert_score": expert_score,
                "problems": probs
            })
            
        lvl_progress = round((lvl_solved / lvl_total * 100), 1) if lvl_total > 0 else 0
        
        roadmap_levels.append({
            "name": lvl_name,
            "is_opted_in": is_opted_in,
            "total": lvl_total,
            "solved": lvl_solved,
            "progress_pct": lvl_progress,
            "categories": categories_data
        })
        
    context = {
        "roadmap_levels": roadmap_levels
    }
    return render(request, "roadmap.html", context)

@csrf_exempt
def toggle_roadmap_optin(request):
    if request.method == "POST":
        level_name = request.POST.get("level_name")
        opted_in = request.POST.get("opted_in") == "true"
        
        if opted_in:
            RoadmapOptIn.objects.get_or_create(level_name=level_name)
        else:
            RoadmapOptIn.objects.filter(level_name=level_name).delete()
            
        return JsonResponse({"status": "SUCCESS"})
    return JsonResponse({"status": "ERROR", "message": "Invalid request method."})

def company_prep(request):
    solved_problems_ids = set(Submission.objects.filter(status='PASS').values_list('problem_id', flat=True).distinct())
    
    target_company = request.GET.get('company', 'Zoho')
    difficulty = request.GET.get('difficulty', '')
    
    # Filter problems asked by target company
    # Using icontains or word matching on Problem.companies
    problems = Problem.objects.filter(companies__icontains=target_company)
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
        
    total_count = problems.count()
    solved_count = problems.filter(id__in=solved_problems_ids).count()
    progress_pct = round((solved_count / total_count * 100), 1) if total_count > 0 else 0
    
    for p in problems:
        p.is_solved = p.id in solved_problems_ids
        
    indian_companies = ["Zoho", "TCS", "Infosys", "Wipro", "Cognizant", "Flipkart", "Paytm", "Swiggy", "Zomato", "PhonePe", "CRED"]
    
    context = {
        "selected_company": target_company,
        "selected_difficulty": difficulty,
        "companies": indian_companies,
        "problems": problems,
        "total_count": total_count,
        "solved_count": solved_count,
        "progress_pct": progress_pct
    }
    return render(request, "company_prep.html", context)

def help_page(request):
    return render(request, "help.html")
