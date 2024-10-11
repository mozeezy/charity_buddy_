from django.urls import path
from .consumers import ReportProgressConsumer

websocket_urlpatterns = [
    path("ws/reports/progress/<str:task_group_id>/", ReportProgressConsumer.as_asgi()),
]
