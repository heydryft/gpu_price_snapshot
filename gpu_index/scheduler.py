import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from gpu_index.config import Config
from gpu_index.pipeline import run_fetch

logger = logging.getLogger(__name__)


def start_scheduler(config: Config) -> None:
    scheduler = BlockingScheduler()

    def fetch_job() -> None:
        try:
            run_fetch(config)
        except Exception:
            logger.exception("Scheduled fetch failed")

    scheduler.add_job(
        fetch_job,
        trigger=IntervalTrigger(hours=config.fetch_interval_hours),
        id="gpu_price_fetch",
        name="GPU Price Fetch",
        replace_existing=True,
    )

    def shutdown(signum: int, _frame: object) -> None:
        logger.info("Received signal %s, shutting down scheduler", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Running initial fetch...")
    fetch_job()

    logger.info(
        "Scheduler started (interval=%s hours). Press Ctrl+C to stop.",
        config.fetch_interval_hours,
    )
    scheduler.start()
