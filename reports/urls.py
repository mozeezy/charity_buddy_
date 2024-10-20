from django.urls import path
from .views import (
    FileUploadView,
    FetchReportView,
    DonorReportsListView,
    ReportStatusView,
    AllReportsURLsView,
    DownloadSelectedReportsView,
)

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    path("get-report/", FetchReportView.as_view(), name="get-report"),
    path(
        "donor-reports-list/", DonorReportsListView.as_view(), name="donor-reports-list"
    ),
    path("status/<str:task_id>/", ReportStatusView.as_view(), name="report-status"),
    path("download-zip/", DownloadSelectedReportsView.as_view(), name="download-zip"),
    path("all-reports-urls/", AllReportsURLsView.as_view(), name="all-reports-urls"),
]
