import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ReportProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):

        self.task_group_id = self.scope["url_route"]["kwargs"]["task_group_id"]
        self.room_group_name = f"report_progress_{self.task_group_id}"


        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def report_progress(self, event):

        progress = event["progress"]
        status = event["status"]

        await self.send(
            text_data=json.dumps(
                {
                    "progress": progress,
                    "status": status,
                }
            )
        )
