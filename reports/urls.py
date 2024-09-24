from django.urls import path
from .views import FileUploadView, GenerateReportView

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    path(
        "generate/<str:donor_id>/", GenerateReportView.as_view(), name="generate-report"
    ),
]
