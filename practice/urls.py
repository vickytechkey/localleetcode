from django.urls import path
from practice import views

app_name = 'practice'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('problems/', views.problems_bank, name='problems'),
    path('practice/<str:problem_id>/', views.practice_sandbox, name='practice'),
    path('practice/<str:problem_id>/run/', views.run_code, name='run_code'),
    path('practice/<str:problem_id>/submit/', views.submit_code, name='submit_code'),
    path('roadmap/', views.roadmap, name='roadmap'),
    path('help/', views.help_page, name='help'),
]
