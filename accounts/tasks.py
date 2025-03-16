from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.core.mail import send_mail
from django.utils import timezone
from .models import Task
from taskmanager.settings import DEFAULT_FROM_EMAIL
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_task_assignment_email(self, task_id):
    try:
        task = Task.objects.get(id=task_id)
        subject = f'New Task Assigned: {task.title}'
        message = f'You have been assigned a new task:\n\nTitle: {task.title}\nDescription: {task.description}\nDue Date: {task.due_date}'
        recipient_list = [task.user.email]
        send_mail(subject, message, DEFAULT_FROM_EMAIL, recipient_list)
    except Exception as exc:
        logger.error(f"Failed to send email for task {task_id}: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
             logger.error(f"Max retries exceeded for task {task_id}. Email not sent.")

@shared_task(bind=True, max_retries=3, default_retry_delay=30)  # Retry 3 times with a 30-second delay
def send_task_deadline_reminder(self):
    try:
        now = timezone.now()
        deadline = now + timezone.timedelta(hours=24)
        tasks = Task.objects.filter(due_date__lte=deadline, due_date__gt=now)

        for task in tasks:
            subject = f'Task Deadline Approaching: {task.title}'
            message = f'Your task deadline is within 24 hours:\n\nTitle: {task.title}\nDescription: {task.description}\nDue Date: {task.due_date}'
            recipient_list = [task.user.email]
            send_mail(subject, message, DEFAULT_FROM_EMAIL, recipient_list)
    except Exception as exc:
        logger.error(f"Failed to send deadline reminders: {exc}")
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Max retries exceeded for deadline reminders. Emails not sent.")