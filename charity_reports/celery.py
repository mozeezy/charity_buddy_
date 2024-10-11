import os
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "charity_reports.settings")


app = Celery("charity_reports")


app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()


app.conf.update(
    task_ignore_result=False,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
    worker_redirect_stdouts_level="INFO",
)

app.finalize()
