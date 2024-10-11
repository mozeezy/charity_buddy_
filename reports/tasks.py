import os
import logging
import re
from celery import shared_task
from google.cloud import storage
from google.oauth2 import service_account
from django.conf import settings
from donations.models import Donor, Donation
from .models import Report
from .utils import generate_donor_report
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import redis

logger = logging.getLogger(__name__)


r = redis.Redis(host="localhost", port=6379, db=0)


def upload_report_to_gcs(report_file, file_name):
    try:
        credentials_path = os.getenv("GS_CREDENTIALS")
        if not credentials_path:
            raise ValueError(
                "Google Cloud credentials path not found in environment variables."
            )

        logger.info(f"Loading Google Cloud credentials from: {credentials_path}")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )

        client = storage.Client(credentials=credentials)
        bucket_name = settings.GS_BUCKET_NAME
        bucket = client.bucket(bucket_name)

        blob = bucket.blob(f"charity_reports/{file_name}")
        report_file.seek(0)
        blob.upload_from_file(report_file, content_type="application/pdf")

        signed_url = blob.generate_signed_url(
            version="v4", expiration=604800, method="GET"
        )

        logger.info(f"File uploaded successfully to GCS: {signed_url}")
        return signed_url

    except Exception as e:
        logger.error(f"Failed to upload report to GCS: {e}")
        raise


@shared_task(bind=True)
def process_donor_report(self, donor_id, total_tasks, task_group_id):
    channel_layer = get_channel_layer()
    room_group_name = f"report_progress_{task_group_id}"
    donor = None

    try:
        logger.info(f"Starting report generation for donor ID: {donor_id}")

        r.set(f"task_progress_{self.request.id}", 0)
        r.expire(f"task_progress_{self.request.id}", 600)

        self.update_state(state="STARTED", meta={"progress": 10})
        update_overall_progress(room_group_name, total_tasks, task_group_id)

        donor = Donor.objects.get(donor_id=donor_id)
        donations = Donation.objects.filter(donor=donor)

        pdf_buffer = generate_donor_report(donor, donations)
        logger.info(f"Report generated successfully for donor ID: {donor_id}")
        r.set(f"task_progress_{self.request.id}", 50)
        update_overall_progress(room_group_name, total_tasks, task_group_id)

        safe_first_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.first_name.lower())
        safe_last_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.last_name.lower())
        file_name = f"{donor.donor_id}_{safe_first_name}_{safe_last_name}_report.pdf"
        public_url = upload_report_to_gcs(pdf_buffer, file_name)

        r.set(f"task_progress_{self.request.id}", 90)
        update_overall_progress(room_group_name, total_tasks, task_group_id)

        Report.objects.create(donor=donor, file_path=public_url, status="SUCCESS")
        logger.info(f"Report entry created for donor ID: {donor_id}")

        r.set(f"task_progress_{self.request.id}", 100)
        update_overall_progress(room_group_name, total_tasks, task_group_id)

        return f"Report for {donor.donor_id} generated successfully."

    except Donor.DoesNotExist as e:
        error_message = f"Donor with ID {donor_id} does not exist."
        logger.error(error_message)

        self.update_state(
            state="FAILURE", meta={"progress": 100, "error": error_message}
        )
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "report_progress",
                "progress": 100,
                "status": "FAILED",
                "error": error_message,
            },
        )
        raise e

    except Exception as e:
        error_message = f"Failed to generate report for donor ID {donor_id}: {e}"
        logger.error(error_message)

        self.update_state(state="FAILURE", meta={"progress": 100, "error": str(e)})
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                "type": "report_progress",
                "progress": 100,
                "status": "FAILED",
                "error": str(e),
            },
        )
        if donor:
            Report.objects.create(
                donor=donor, file_path="", status="FAILED", error_log=str(e)
            )

        raise e


def update_overall_progress(room_group_name, total_tasks, task_group_id):

    total_progress = 0

    for task_key in r.keys(f"task_progress_*"):
        total_progress += int(r.get(task_key))

    overall_progress = total_progress / (total_tasks * 100) * 100

    async_to_sync(get_channel_layer().group_send)(
        room_group_name,
        {
            "type": "report_progress",
            "progress": overall_progress,
            "status": "IN_PROGRESS" if overall_progress < 100 else "SUCCESS",
        },
    )
