from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from .models import Task
from .serializers import TaskSerializer
from .tasks import send_task_assignment_email
from concurrent.futures import ThreadPoolExecutor
from django.db.models import Count, Q
from rest_framework.views import APIView
from rest_framework import status
from django.core.cache import cache
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

class LoginView(generics.GenericAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        user = User.objects.filter(username=username).first()

        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response({'error': 'Invalid credentials'}, status=400)

class TaskFilter(filters.FilterSet):
    priority = filters.CharFilter(lookup_expr='iexact')
    status = filters.CharFilter(lookup_expr='iexact')
    due_date = filters.DateFilter(lookup_expr='exact')

    class Meta:
        model = Task
        fields = ['priority', 'status', 'due_date']

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = TaskFilter

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        cache_key = f"task_list_{request.user.id}"
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.info("Returning task list from cache")
            return Response(cached_response, status=status.HTTP_200_OK)

        logger.info("Querying database for task list")
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        response_data = serializer.data

        cache.set(cache_key, response_data, timeout=60)

        return Response(response_data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        cache_key = f"task_list_{self.request.user.id}"
        cache.delete(cache_key)
        send_task_assignment_email.delay(task.id)
        self.send_websocket_message('task_created', task)
    
    def send_websocket_message(self, action, task):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'tasks',
            {
                'type': 'task_message',
                'message': {
                    'action': action,
                    'task': TaskSerializer(task).data
                }
            }
        )

class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        task = serializer.save()
        cache_key = f"task_list_{self.request.user.id}"
        cache.delete(cache_key)
        # super().perform_update(serializer)
        self.send_websocket_message('task_updated', task)
    
    def perform_destroy(self, instance):
        cache_key = f"task_list_{self.request.user.id}"
        cache.delete(cache_key)
        self.send_websocket_message('task_deleted', instance)
        super().perform_destroy(instance)
    
    def send_websocket_message(self, action, task):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'tasks',
            {
                'type': 'task_message',
                'message': {
                    'action': action,
                    'task': TaskSerializer(task).data
                }
            }
        )

class TaskReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        tasks = Task.objects.filter(user=user)

        with ThreadPoolExecutor() as executor:
            completed_future = executor.submit(self._get_completed_tasks, tasks)
            pending_future = executor.submit(self._get_pending_tasks, tasks)
            priority_future = executor.submit(self._get_tasks_by_priority, tasks)

            completed_tasks = completed_future.result()
            pending_tasks = pending_future.result()
            tasks_by_priority = priority_future.result()

        report = {
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "tasks_by_priority": tasks_by_priority,
        }

        return Response(report, status=status.HTTP_200_OK)

    def _get_completed_tasks(self, tasks):
        return tasks.filter(status='done').count()

    def _get_pending_tasks(self, tasks):
        return tasks.filter(~Q(status='done')).count()

    def _get_tasks_by_priority(self, tasks):
        return tasks.values('priority').annotate(count=Count('priority')).order_by('priority')