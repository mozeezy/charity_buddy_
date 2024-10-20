from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
from storages.backends.gcloud import GoogleCloudStorage
from donations.models import Donor, Donation
from reports.models import Cause, Report
import chardet
from .tasks import process_donor_report
from collections import defaultdict
from django.http import HttpResponse
from rest_framework.pagination import PageNumberPagination
from celery.result import AsyncResult
import uuid
import redis
import zipfile
from django.conf import settings
from google.cloud import storage
import os
import io
import tempfile
from google.oauth2 import service_account
from urllib.parse import urlparse, parse_qs


r = redis.Redis(host="localhost", port=6379, db=0)


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        google_storage = GoogleCloudStorage()
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_extension = file.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls", "csv"]:
            return Response(
                {"error": "Invalid file type. Only Excel or CSV files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = google_storage.save(f"temp/{file.name}", file)

        try:

            with google_storage.open(file_path, "rb") as raw_file:
                raw_data = raw_file.read()
                result = chardet.detect(raw_data)
                encoding = result["encoding"]
                raw_file.seek(0)

                if file_extension == "csv":
                    df = pd.read_csv(raw_file, encoding=encoding)
                else:
                    df = pd.read_excel(raw_file)

            required_columns = [
                "Donor ID",
                "Donation ID",
                "Donor First Name",
                "Donor Last Name",
                "Donor Email",
                "Donation Amount",
                "Date of Donation",
                "Time of Donation",
                "Cause ID",
                "Cause",
            ]
            if not all(column in df.columns for column in required_columns):
                return Response(
                    {
                        "error": f"Missing required columns. Expected: {required_columns}"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            donations_per_donor = defaultdict(list)

            for _, row in df.iterrows():
                donor, _ = Donor.objects.get_or_create(
                    donor_id=row["Donor ID"],
                    defaults={
                        "first_name": row["Donor First Name"],
                        "last_name": row["Donor Last Name"],
                        "email": row["Donor Email"],
                        "phone": row.get("Phone Number", None),
                        "address": row.get("Address", None),
                    },
                )

                cause, _ = Cause.objects.get_or_create(
                    cause_id=row["Cause ID"],
                    defaults={
                        "name": row["Cause"],
                        "description": row.get("Description", ""),
                        "images": row.get("Images", None),
                    },
                )

                try:
                    donation_date = datetime.strptime(
                        row["Date of Donation"], "%Y-%m-%d"
                    ).date()
                    donation_time = datetime.strptime(
                        row["Time of Donation"], "%I:%M %p"
                    ).time()
                except ValueError as ve:
                    return Response(
                        {
                            "error": f"Invalid date or time format in row: {row}. Error: {str(ve)}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                donation = Donation.objects.create(
                    donor=donor,
                    donation_id=row["Donation ID"],
                    amount=row["Donation Amount"],
                    date=donation_date,
                    time=donation_time,
                    cause=cause,
                    payment_type=row.get("Payment Type", None),
                    recurrence=row.get("Recurrence Status", None),
                    tax_receipt_status=row.get("Tax Receipt Status", False),
                )

                donations_per_donor[donor.donor_id].append(donation)

            task_group_id = str(uuid.uuid4())

            total_tasks = len(donations_per_donor)
            r.set(f"task_group_total_{task_group_id}", total_tasks)

            for donor_id in donations_per_donor.keys():
                process_donor_report.delay(donor_id, total_tasks, task_group_id)

        except Exception as e:
            return Response(
                {"error": f"Error processing file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            google_storage.delete(file_path)

        return Response(
            {
                "message": "File uploaded and processed successfully!",
                "task_group_id": task_group_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class FetchReportView(APIView):
    def get(self, request, donor_id, *args, **kwargs):

        google_storage = GoogleCloudStorage()

        try:

            report = Report.objects.filter(
                donor__donor_id=donor_id, status="SUCCESS"
            ).latest("date_generated")

            if google_storage.exists(report.file_path):
                with google_storage.open(report.file_path, "rb") as f:
                    response = HttpResponse(f.read(), content_type="application/pdf")
                    response["Content-Disposition"] = (
                        f'inline; filename="{report.donor.first_name}_{report.donor.last_name}_report.pdf"'
                    )
                    return response
            else:
                return HttpResponse(
                    "Report file not found in Google Cloud Storage.", status=404
                )

        except Report.DoesNotExist:
            return HttpResponse(
                "No successful report found for this donor.", status=404
            )


class DonorReportsListView(APIView):
    def get(self, request):
        try:
            search_query = request.query_params.get("search", "")
            sort_by = request.query_params.get("sort_by", "full_name")
            sort_order = request.query_params.get("sort_order", "asc")

            donors = Donor.objects.all()

            if search_query:
                donors = donors.filter(
                    first_name__icontains=search_query
                ) | donors.filter(last_name__icontains=search_query)

            if sort_by == "full_name":
                sort_by = "first_name"
            if sort_order == "desc":
                sort_by = f"-{sort_by}"

            donors = donors.order_by(sort_by)

            donor_reports = []
            for donor in donors:
                latest_report = (
                    Report.objects.filter(donor=donor, status="SUCCESS")
                    .order_by("-date_generated")
                    .first()
                )
                if latest_report:
                    donor_reports.append(
                        {
                            "donor_id": donor.donor_id,
                            "full_name": f"{donor.first_name} {donor.last_name}",
                            "email": donor.email,
                            "report_url": latest_report.file_path,
                            "status": latest_report.status,
                        }
                    )

            paginator = PageNumberPagination()
            paginator.page_size = 10
            paginated_reports = paginator.paginate_queryset(donor_reports, request)

            return paginator.get_paginated_response(paginated_reports)

        except Exception as e:
            return Response(
                {"error": f"Error fetching donor reports: {str(e)}"}, status=500
            )


class ReportStatusView(APIView):
    def get(self, request, task_id):
        try:

            task_result = AsyncResult(task_id)

            if task_result.state == "PENDING":
                response = {"status": "PENDING", "progress": 0}
            elif task_result.state == "PROGRESS":
                response = {
                    "status": "IN_PROGRESS",
                    "progress": task_result.info.get("progress", 0),
                }
            elif task_result.state == "SUCCESS":
                response = {
                    "status": "SUCCESS",
                    "progress": 100,
                    "message": task_result.result,
                }
            elif task_result.state == "FAILURE":
                response = {
                    "status": "FAILED",
                    "progress": 100,
                    "error": str(task_result.info),
                }
            else:
                response = {"status": task_result.state, "progress": 0}

            return Response(response)

        except Exception as e:
            return Response(
                {"error": f"Error fetching task status: {str(e)}"}, status=500
            )


class DownloadZipView(APIView):
    def post(self, request, *args, **kwargs):
        report_urls = request.data.get("reports", [])

        if not report_urls:
            return Response(
                {"error": "No reports selected"}, status=status.HTTP_400_BAD_REQUEST
            )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            client = storage.Client()
            bucket = client.bucket(settings.GS_BUCKET_NAME)

            for report_url in report_urls:
                blob = bucket.blob(report_url)
                file_data = blob.download_as_bytes()

                filename = os.path.basename(report_url)
                zf.writestr(filename, file_data)

        zip_buffer.seek(0)

        response = HttpResponse(zip_buffer, content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="donor_reports.zip"'

        return response


class AllReportsURLsView(APIView):
    def get(self, request):

        try:
            search_query = request.query_params.get("search", "")
            donors = Donor.objects.all()

            if search_query:
                donors = donors.filter(
                    first_name__icontains=search_query
                ) | donors.filter(last_name__icontains(search_query))

            all_reports = []

            for donor in donors:
                latest_report = (
                    Report.objects.filter(donor=donor, status="SUCCESS")
                    .order_by("-date_generated")
                    .first()
                )
                if latest_report:
                    all_reports.append(
                        {
                            "donor_id": donor.donor_id,
                            "full_name": f"{donor.first_name} {donor.last_name}",
                            "email": donor.email,
                            "report_url": latest_report.file_path,
                        }
                    )

            return Response(all_reports, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error fetching all reports: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DownloadSelectedReportsView(APIView):
    def post(self, request):
        try:
            report_urls = request.data.get("report_urls", [])
            if not report_urls:
                return Response(
                    {"error": "No reports selected."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            credentials_path = os.getenv("GS_CREDENTIALS")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            client = storage.Client(credentials=credentials)
            bucket_name = settings.GS_BUCKET_NAME
            bucket = client.bucket(bucket_name)

            temp_zip = tempfile.NamedTemporaryFile(delete=False)
            zip_file_path = temp_zip.name

            with zipfile.ZipFile(temp_zip, "w") as zipf:
                for report_url in report_urls:

                    parsed_url = urlparse(report_url)
                    file_path = parsed_url.path.replace(f"/{bucket_name}/", "")

                    blob = bucket.blob(file_path)
                    if not blob.exists():
                        return Response(
                            {"error": f"File not found: {file_path}"},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    with tempfile.NamedTemporaryFile(delete=False) as temp_report_file:

                        blob.download_to_filename(temp_report_file.name)

                        zipf.write(temp_report_file.name, os.path.basename(file_path))

            temp_zip.close()

            with open(zip_file_path, "rb") as zipf:
                response = HttpResponse(zipf.read(), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="reports.zip"'

            os.remove(zip_file_path)

            return response

        except Exception as e:
            return Response(
                {"error": f"Error creating ZIP file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
