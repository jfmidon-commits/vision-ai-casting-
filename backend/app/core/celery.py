from celery import Celery
from app.config import settings

celery_app = Celery(
    "vision_ai_casting",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.services.ai_service"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# Beat schedule
celery_app.conf.beat_schedule = {
    "cleanup-old-analyses": {
        "task": "app.tasks.cleanup.cleanup_old_analyses",
        "schedule": 86400.0,  # Daily
    },
    "generate-daily-reports": {
        "task": "app.tasks.reports.generate_daily_summary",
        "schedule": 3600.0,  # Hourly
    },
}
