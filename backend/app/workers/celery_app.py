from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "koptumbuh",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.router",
        "app.workers.validator",
        "app.workers.dispatcher",
        "app.workers.recommendations",
        "app.workers.supply_chain",
        "app.workers.relationship",
        "app.workers.price_scraper",
        "app.workers.backup",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,
    task_time_limit=600,
    worker_max_tasks_per_child=100,
)

celery_app.conf.beat_schedule = {
    "generate-recommendations": {
        "task": "app.workers.recommendations.generate_all_recommendations",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    "scrape-ecommerce-prices": {
        "task": "app.workers.price_scraper.scrape_ecommerce_prices",
        "schedule": crontab(hour=6, minute=0),
    },
    "morning-price-broadcast": {
        "task": "app.workers.dispatcher.send_morning_broadcast",
        "schedule": crontab(hour=7, minute=0),
    },
    "daily-operator-briefing": {
        "task": "app.workers.recommendations.generate_daily_briefing",
        "schedule": crontab(hour=7, minute=15),
    },
    "auto-generate-purchase-orders": {
        "task": "app.workers.supply_chain.auto_generate_po",
        "schedule": crontab(hour=7, minute=30),
    },
    "member-milestone-check": {
        "task": "app.workers.relationship.check_member_milestones",
        "schedule": crontab(hour=8, minute=0),
    },
    "winback-campaign": {
        "task": "app.workers.relationship.run_winback_campaign",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
    "onboarding-check": {
        "task": "app.workers.relationship.send_onboarding_messages",
        "schedule": crontab(hour=9, minute=0),
    },
    "daily-db-backup": {
        "task": "app.workers.backup.run_backup",
        "schedule": crontab(hour=2, minute=0),
    },
}
