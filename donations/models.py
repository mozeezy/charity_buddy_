from django.db import models


class Donor(models.Model):
    donor_id = models.CharField(max_length=20, unique=True, primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.donor_id})"


class Donation(models.Model):
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    donation_id = models.CharField(max_length=20, unique=True, primary_key=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    time = models.TimeField()
    payment_type = models.CharField(max_length=50)
    recurrence = models.CharField(
        max_length=20, choices=[("one-time", "One-Time"), ("recurring", "Recurring")]
    )
    cause = models.ForeignKey(
        "reports.Cause", on_delete=models.CASCADE, null=True, blank=True
    )

    tax_receipt_status = models.BooleanField(default=False)

    def __str__(self):
        return f"Donation {self.donation_id} by {self.donor.first_name} {self.donor.last_name}"
