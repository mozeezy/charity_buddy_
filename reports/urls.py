from django.urls import path
from .views import FileUploadView, FetchReportView

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    path("get-report/", FetchReportView.as_view(), name="get-report"),
]
