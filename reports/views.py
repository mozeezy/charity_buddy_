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


class FileUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES.get("file")

        # Validate if the file exists
        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file type (Excel or CSV)
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in [".xlsx", ".xls", ".csv"]:
            return Response(
                {"error": "Invalid file type. Only Excel or CSV files are allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save the file temporarily
        file_path = default_storage.save(f"temp/{file.name}", file)
        file_full_path = os.path.join(default_storage.location, file_path)

        try:
            # Process CSV or Excel files
            if file_extension == ".csv":
                with open(file_full_path, "rb") as raw_file:
                    raw_data = raw_file.read()
                    result = chardet.detect(raw_data)
                    encoding = result["encoding"]

                df = pd.read_csv(file_full_path, encoding=encoding)

            elif file_extension in [".xlsx", ".xls"]:
                df = pd.read_excel(file_full_path)

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

            # Process each row in the DataFrame
            for _, row in df.iterrows():
                # Get or create the donor
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

                # Get or create the cause using Cause ID and Cause Name
                cause_id = row["Cause ID"]  # The Cause ID from the file
                cause_name = row["Cause"]  # The Cause Name from the file

                # FileUploadView - handle images being nullable
                cause, created = Cause.objects.get_or_create(
                    cause_id=cause_id,  # Use Cause ID as the primary key
                    defaults={
                        "name": cause_name,
                        "description": row.get("Description", ""),
                        "images": row.get(
                            "Images", None
                        ),  # Provide None if images are missing
                    },
                )

                # Parse the date and time
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
                    ).time()  # For example, '02:30 PM'
                except ValueError:
                    return Response(
                        {"error": f"Invalid time format in row: {row}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create the donation entry
                Donation.objects.create(
                    donor=donor,
                    donation_id=row["Donation ID"],
                    amount=row["Donation Amount"],
                    date=donation_date,  # Parsed date
                    time=donation_time,  # Parsed time
                    cause=cause,  # Link to Cause model using cause_id
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
            # Clean up the temporary file
            if os.path.exists(file_full_path):
                os.remove(file_full_path)

        return Response(
            {"message": "File uploaded and processed successfully!"},
            status=status.HTTP_200_OK,
        )
