"""
Celery application instance.

Redis is used as both broker and result backend — it's already a
hard dependency (docker-compose) and there's no need for a separate
result store at this scale. Tasks are organized by domain under
``app/tasks/``; ``include`` below is how Celery discovers them, since
we're not using Django-style autodiscovery.

Run the worker with::

    celery -A app.core.celery_app worker --loglevel=info

Run the beat scheduler (for periodic account syncs) with::

    celery -A app.core.celery_app beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "wealthflow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.ingestion",
        "app.tasks.classification",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Tasks touch MSSQL + external bank APIs — ack-late + reject-on-
    # worker-lost means a crashed worker's in-flight sync gets
    # redelivered rather than silently dropped.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Ingestion tasks are I/O-bound (HTTP + DB), not CPU-bound, so
    # workers can hold several in flight per process without
    # contention; keep it conservative until we have real timing data.
    worker_prefetch_multiplier=4,
    # Periodic task schedule — sync all due bank connections every 4h.
    beat_schedule={
        "sync-all-due-connections": {
            "task": "ingestion.sync_all_due_connections",
            "schedule": crontab(minute=0, hour="*/4"),
        },
    },
)
