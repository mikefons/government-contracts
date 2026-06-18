"""Optional background scheduler for periodic ingestion.
Enabled only when ENABLE_SCHEDULER=true."""
from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .database import SessionLocal
from .ingest import ingest_find_a_tender
from .logging_mw import logger


def _job():
    db = SessionLocal()
    try:
        n = ingest_find_a_tender(db)
        logger.info("scheduled ingest upserted=%s", n)
    except Exception:
        logger.exception("scheduled ingest failed")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(_job, "interval", minutes=settings.ingest_interval_minutes,
                  id="ingest", next_run_time=None)
    sched.start()
    return sched
