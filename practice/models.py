from django.db import models
from django.utils import timezone

class Problem(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=200)
    difficulty = models.CharField(max_length=20) # Easy, Medium, Hard
    category = models.CharField(max_length=100) # e.g. Arrays & Hashing
    description = models.TextField()
    concepts = models.TextField(blank=True, default='') # comma-separated
    hints = models.TextField(blank=True, default='') # semicolon-separated
    function_name = models.CharField(max_length=100) # e.g. twoSum
    input_types = models.TextField() # JSON string representation, e.g. ["List[int]", "int"]
    companies = models.TextField(blank=True, default='') # comma-separated e.g. TCS, Infosys, Zoho
    solution_code = models.TextField(blank=True, default='') # working reference python solution

    def __str__(self):
        return f"{self.id}: {self.title}"

    @property
    def concepts_list(self):
        return [c.strip() for c in self.concepts.split(",") if c.strip()]

    @property
    def hints_list(self):
        return [h.strip() for h in self.hints.split(";") if h.strip()]

    @property
    def companies_list(self):
        return [c.strip() for c in self.companies.split(",") if c.strip()]

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    inputs = models.TextField() # JSON string representing input list
    expected_output = models.TextField() # JSON string representing output
    comparison_mode = models.CharField(max_length=50, default='Exact') # Exact, Ignore Order

    def __str__(self):
        return f"TC for {self.problem_id}"

class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    code = models.TextField()
    status = models.CharField(max_length=20) # PASS, FAIL, ERROR
    execution_time_ms = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.problem_id} - {self.status} @ {self.timestamp}"

class DailyActivity(models.Model):
    date = models.DateField(primary_key=True)
    attempts = models.IntegerField(default=0)
    solved = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.date}: Attempts={self.attempts}, Solved={self.solved}"

class Goal(models.Model):
    type = models.CharField(max_length=50) # Daily, Weekly, Monthly
    target = models.IntegerField()
    progress = models.IntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    difficulty = models.CharField(max_length=20, blank=True, null=True) # Optional e.g. Easy
    category = models.CharField(max_length=100, blank=True, null=True) # Optional e.g. Arrays & Hashing

    def __str__(self):
        return f"{self.type} Goal: {self.calculated_progress}/{self.target}"

    @property
    def calculated_progress(self):
        qs = Submission.objects.filter(
            status='PASS',
            timestamp__gte=self.created_at,
            timestamp__date__gte=self.start_date,
            timestamp__date__lte=self.end_date
        )
        if self.difficulty:
            qs = qs.filter(problem__difficulty=self.difficulty)
        if self.category:
            qs = qs.filter(problem__category=self.category)
        return qs.values('problem_id').distinct().count()

class RoadmapOptIn(models.Model):
    level_name = models.CharField(max_length=50, unique=True) # e.g. Beginner, Intermediate, etc.
    opted_in_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.level_name

