from django.db import models


class Cause(models.Model):
    cause_id = models.CharField(max_length=20, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    amount_raised = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    people_helped = models.IntegerField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.name


class Report(models.Model):
    donor = models.ForeignKey("donations.Donor", on_delete=models.CASCADE)
    file_path = models.TextField()
    date_generated = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=[("SUCCESS", "Success"), ("FAILED", "Failed")]
    )
    error_log = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report for {self.donor.first_name} {self.donor.last_name} - {self.date_generated.strftime('%Y-%m-%d')}"
