import os
import logging
import re
from celery import shared_task, current_task
from google.cloud import storage
from google.oauth2 import service_account
from django.conf import settings
from donations.models import Donor, Donation
from .models import Report
from .utils import generate_donor_report
from django.core.files.base import ContentFile

# Set up a logger for this module
logger = logging.getLogger(__name__)


def upload_report_to_gcs(report_file, file_name):
    try:
        # Load credentials explicitly using the environment variable
        credentials_path = os.getenv("GS_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "Google Cloud credentials path not found in environment variables."
            )

        logger.info(f"Loading Google Cloud credentials from: {credentials_path}")

        # Load the credentials
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )

        # Initialize the Google Cloud Storage client
        client = storage.Client(credentials=credentials)
        bucket_name = settings.GS_BUCKET_NAME
        bucket = client.bucket(bucket_name)

        # Create a blob for the file and upload it
        blob = bucket.blob(f"charity_reports/{file_name}")

        # Ensure the file pointer is at the beginning
        report_file.seek(0)
        blob.upload_from_file(report_file, content_type="application/pdf")

        # Generate a signed URL valid for 7 days
        signed_url = blob.generate_signed_url(
            version="v4", expiration=604800, method="GET"  # 7 days in seconds
        )

        logger.info(f"File uploaded successfully to GCS: {signed_url}")
        return signed_url

    except Exception as e:
        logger.error(f"Failed to upload report to GCS: {e}")
        # Raise the caught exception instead of creating a new one without a specific type
        raise


@shared_task(bind=True)
def process_donor_report(self, donor_id):
    donor = None
    try:
        logger.info(f"Starting report generation for donor ID: {donor_id}")
        # Update task state to indicate the start of the process
        self.update_state(state="STARTED", meta={"progress": 10})

        # Retrieve the donor and donations
        donor = Donor.objects.get(donor_id=donor_id)
        donations = Donation.objects.filter(donor=donor)

        # Generate the report
        pdf_buffer = generate_donor_report(donor, donations)
        logger.info(f"Report generated successfully for donor ID: {donor_id}")

        # Update progress
        self.update_state(state="PROGRESS", meta={"progress": 50})

        # Sanitize file name
        safe_first_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.first_name.lower())
        safe_last_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.last_name.lower())
        file_name = f"{donor.donor_id}_{safe_first_name}_{safe_last_name}_report.pdf"

        # Upload the report to GCS
        public_url = upload_report_to_gcs(pdf_buffer, file_name)
        logger.info(f"Report uploaded to GCS successfully. URL: {public_url}")

        # Update progress
        self.update_state(state="PROGRESS", meta={"progress": 90})

        # Save the report's URL in the database
        Report.objects.create(donor=donor, file_path=public_url, status="SUCCESS")
        logger.info(f"Report entry created in the database for donor ID: {donor_id}")

        # Final progress update
        self.update_state(state="SUCCESS", meta={"progress": 100})
        return f"Report for {donor.donor_id} generated successfully."

    except Donor.DoesNotExist as e:
        logger.error(f"Donor with ID {donor_id} does not exist.")
        # Raising the exception so that Celery can handle it and mark the task as failed
        raise e

    except Exception as e:
        logger.error(f"Failed to generate report for donor ID {donor_id}: {e}")
        # Create a failed report entry if the donor is available
        if donor:
            Report.objects.create(
                donor=donor, file_path="", status="FAILED", error_log=str(e)
            )
        # Raising the exception so that Celery can handle it and mark the task as failed
        raise
