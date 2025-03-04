import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_api.settings")

app = Celery("social_media_api")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    print(f"Request: {self.request!r}")
