import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Task
from .serializers import TaskSerializer

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('tasks', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('tasks', self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        await self.channel_layer.group_send(
            'tasks',
            {
                'type': 'task_message',
                'message': message
            }
        )

    async def task_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))