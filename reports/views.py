from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
import pandas as pd
import os
from django.core.files.storage import default_storage
from donations.models import Donor, Donation
from reports.models import Cause
import chardet
from django.http import HttpResponse
from .utils import generate_donor_report


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in [".xlsx", ".xls", ".csv"]:
            return Response(
                {"error": "Invalid file type. Only Excel or CSV files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = default_storage.save(f"temp/{file.name}", file)
        file_full_path = os.path.join(default_storage.location, file_path)

        try:

            if file_extension == ".csv":
                with open(file_full_path, "rb") as raw_file:
                    raw_data = raw_file.read()
                    result = chardet.detect(raw_data)
                    encoding = result["encoding"]

                df = pd.read_csv(file_full_path, encoding=encoding)

            elif file_extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file_full_path)

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

            for _, row in df.iterrows():

                donor, created = Donor.objects.get_or_create(
                    donor_id=row["Donor ID"],
                    defaults={
                        "first_name": row["Donor First Name"],
                        "last_name": row["Donor Last Name"],
                        "email": row["Donor Email"],
                        "phone": row.get("Phone Number", None),
                        "address": row.get("Address", None),
                    },
                )

                cause_id = row["Cause ID"]
                cause_name = row["Cause"]

                cause, created = Cause.objects.get_or_create(
                    cause_id=cause_id,
                    defaults={
                        "name": cause_name,
                        "description": row.get("Description", ""),
                        "images": row.get("Images", None),
                    },
                )

                try:
                    donation_date = datetime.strptime(
                        row["Date of Donation"], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    return Response(
                        {"error": f"Invalid date format in row: {row}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                try:
                    donation_time = datetime.strptime(
                        row["Time of Donation"], "%I:%M %p"
                    ).time()
                except ValueError:
                    return Response(
                        {"error": f"Invalid time format in row: {row}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                Donation.objects.create(
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

        except Exception as e:
            return Response(
                {"error": f"Error processing file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        finally:

            if os.path.exists(file_full_path):
                os.remove(file_full_path)

        return Response(
            {"message": "File uploaded and processed successfully!"},
            status=status.HTTP_200_OK,
        )


class GenerateReportView(APIView):
    def get(self, request, donor_id, *args, **kwargs):
        try:
            donor = Donor.objects.get(donor_id=donor_id)
            donations = Donation.objects.filter(donor=donor)

            if not donations.exists():
                return HttpResponse("No donations found for this donor.", status=404)

            pdf_buffer = generate_donor_report(donor, donations)

            response = HttpResponse(pdf_buffer, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'inline; filename="{donor.first_name}_{donor.last_name}_report.pdf"'
            )

            return response

        except Donor.DoesNotExist:
            return HttpResponse("Donor not found.", status=404)
