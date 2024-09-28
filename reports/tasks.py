from celery import shared_task
from donations.models import Donor, Donation
from .models import Report
from .utils import generate_donor_report
import re
from django.core.files.base import ContentFile
from storages.backends.gcloud import GoogleCloudStorage


@shared_task(bind=True)
def process_donor_report(self, donor_id):
    # Create an instance of GoogleCloudStorage
    google_storage = GoogleCloudStorage()

    donor = None
    try:
        # Retrieve the donor and all related donations from the database
        donor = Donor.objects.get(donor_id=donor_id)
        donations = Donation.objects.filter(donor=donor)

        # Generate the report with all donations
        pdf_buffer = generate_donor_report(donor, donations)

        # Sanitize and lowercase the first name and last name
        safe_first_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.first_name.lower())
        safe_last_name = re.sub(r"[^a-zA-Z0-9_-]", "", donor.last_name.lower())

        # Format the file name as "donorid_firstname_lastname_report.pdf"
        file_name = f"{donor.donor_id}_{safe_first_name}_{safe_last_name}_report.pdf"
        report_file_path = f"charity_reports/{file_name}"

        # Save the report to Google Cloud Storage
        try:
            google_storage.save(report_file_path, ContentFile(pdf_buffer.getvalue()))

        except Exception as upload_error:

            return f"Failed to upload report to Google Cloud Storage for donor ID {donor_id}: {str(upload_error)}"

        # Mark the report generation as successful in the Report model
        Report.objects.create(donor=donor, file_path=report_file_path, status="SUCCESS")
        return f"Report for {donor.donor_id} generated successfully."

    except Donor.DoesNotExist:
        return f"Donor with ID {donor_id} does not exist."

    except Exception as e:

        if donor:
            Report.objects.create(
                donor=donor, file_path="", status="FAILED", error_log=str(e)
            )

        return f"Failed to generate report for donor ID {donor_id}: {str(e)}"
