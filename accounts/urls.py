from django.urls import path
from .views import RegisterView, LoginView, TaskDetailView, TaskListCreateView, TaskReportView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('tasks/', TaskListCreateView.as_view(), name='task-list-create'),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/report/', TaskReportView.as_view(), name='task-report'),
]