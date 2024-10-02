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


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Create an instance of GoogleCloudStorage
        google_storage = GoogleCloudStorage()

        file = request.FILES.get("file")

        # Validate if the file exists
        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check the file extension to ensure it's an Excel or CSV file
        file_extension = file.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls", "csv"]:
            return Response(
                {"error": "Invalid file type. Only Excel or CSV files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the uploaded file using GoogleCloudStorage
        file_path = google_storage.save(f"temp/{file.name}", file)

        try:
            # Open the file using GoogleCloudStorage
            with google_storage.open(file_path, "rb") as raw_file:
                # Detect file encoding using chardet
                raw_data = raw_file.read()
                result = chardet.detect(raw_data)
                encoding = result["encoding"]
                raw_file.seek(0)  # Reset the file pointer to the beginning

                # Process CSV or Excel files using the detected encoding
                if file_extension == "csv":
                    df = pd.read_csv(raw_file, encoding=encoding)
                else:
                    df = pd.read_excel(raw_file)

            # Required columns
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

            # Collect donations per donor
            donations_per_donor = defaultdict(list)

            for _, row in df.iterrows():
                # Create or get the donor object
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

                # Create or get the cause object
                cause, _ = Cause.objects.get_or_create(
                    cause_id=row["Cause ID"],
                    defaults={
                        "name": row["Cause"],
                        "description": row.get("Description", ""),
                        "images": row.get("Images", None),
                    },
                )

                # Parse the date and time of donation
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

                # Create the donation entry
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

                # Add the donation to the donor's list
                donations_per_donor[donor.donor_id].append(donation)

            # Trigger report generation for each unique donor and collect task IDs
            task_ids = []
            for donor_id in donations_per_donor.keys():
                task = process_donor_report.delay(donor_id)
                task_ids.append(task.id)

        except Exception as e:
            return Response(
                {"error": f"Error processing file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:
            # Delete the uploaded file from Google Cloud Storage
            google_storage.delete(file_path)

        # Return the list of task IDs
        return Response(
            {
                "message": "File uploaded and processed successfully!",
                "task_ids": task_ids,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class FetchReportView(APIView):
    def get(self, request, donor_id, *args, **kwargs):
        # Create an instance of GoogleCloudStorage
        google_storage = GoogleCloudStorage()

        try:
            # Find the latest successful report for the donor
            report = Report.objects.filter(
                donor__donor_id=donor_id, status="SUCCESS"
            ).latest("date_generated")

            # Check if the report file exists in Google Cloud Storage
            if google_storage.exists(report.file_path):
                # Open the file using Google Cloud Storage
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
            search_query = request.query_params.get(
                "search", ""
            )  # Get the search query parameter
            donors = Donor.objects.all()

            # Filter donors by search query if it exists
            if search_query:
                donors = donors.filter(
                    first_name__icontains=search_query
                ) | donors.filter(last_name__icontains=search_query)

            donor_reports = []

            for donor in donors:
                # Get the latest successful report for each donor
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

            # Implement pagination
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Number of reports per page
            paginated_reports = paginator.paginate_queryset(donor_reports, request)

            return paginator.get_paginated_response(paginated_reports)

        except Exception as e:
            return Response(
                {"error": f"Error fetching donor reports: {str(e)}"}, status=500
            )


class ReportStatusView(APIView):
    def get(self, request, task_id):
        try:
            # Get the task result using the provided task_id
            task_result = AsyncResult(task_id)

            # Determine the task status
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
                    "error": str(task_result.info),  # Include error message
                }
            else:
                response = {"status": task_result.state, "progress": 0}

            return Response(response)

        except Exception as e:
            return Response(
                {"error": f"Error fetching task status: {str(e)}"}, status=500
            )
