import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "charity_reports.settings")

app = Celery("charity_reports")

# Load task modules from all registered Django app configs.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks.py in each Django app.
app.autodiscover_tasks()
