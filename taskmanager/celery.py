import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskmanager.settings')

app = Celery('taskmanager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-task-deadline-reminder': {
        'task': 'accounts.tasks.send_task_deadline_reminder',
        'schedule': crontab(minute=0, hour=0),  
    },
}