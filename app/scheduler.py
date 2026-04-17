"""Optional APScheduler hook for nightly forecast retrain (ENABLE_SCHEDULER=1)."""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_retrain() -> None:
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "retrain_job.py"
    try:
        subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except Exception as e:
        logger.exception("retrain_job failed: %s", e)


def init_scheduler(app: Flask) -> None:
    """Start background scheduler if ENABLE_SCHEDULER is set."""
    global _scheduler
    if not app.config.get("ENABLE_SCHEDULER"):
        return
    if _scheduler is not None:
        return
    hour = int(app.config.get("RETRAIN_CRON_HOUR", 3))
    minute = int(app.config.get("RETRAIN_CRON_MINUTE", 0))
    sched = BackgroundScheduler(timezone="UTC")
    sched.add_job(_run_retrain, "cron", hour=hour, minute=minute, id="nightly_retrain")
    sched.start()
    _scheduler = sched
    app.logger.info("APScheduler: nightly retrain at %02d:%02d UTC", hour, minute)
