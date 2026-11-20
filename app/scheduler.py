from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .jobs import fanout_alerts, refresh_all

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        refresh_all,
        "interval",
        minutes=max(5, settings.poll_interval_minutes),
        id="refresh",
        replace_existing=True,
    )
    _scheduler.add_job(
        fanout_alerts,
        "interval",
        minutes=max(5, settings.poll_interval_minutes),
        id="alerts",
        replace_existing=True,
    )
    _scheduler.start()
