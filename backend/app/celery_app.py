from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "dealguard",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.price_collection",
        "app.tasks.history_sync",
        "app.tasks.analysis",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery_app.conf.beat_schedule = {
    "collect-all-tracked-prices": {
        "task": "app.tasks.price_collection.collect_all_tracked_prices",
        "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
    },
    "refresh-stale-analyses": {
        "task": "app.tasks.analysis.refresh_stale_analyses",
        "schedule": crontab(minute=30, hour="*/6"),
    },
}
