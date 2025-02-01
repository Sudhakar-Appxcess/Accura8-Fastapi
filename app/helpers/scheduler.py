# ** Base Modules
from datetime import datetime

# ** External Modules
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler
from logzero import logger
from pytz import timezone


def register_scheduler(app):
    # Initialize the scheduler
    scheduler = BackgroundScheduler(timezone=timezone('Asia/Kolkata'))

    # ----------------------
    def _check_health():
        logger.info(f'Health Pulse -- {datetime.now()}')
    # ----------------------

    # Every 1 Minutes
    scheduler.add_job(_check_health, trigger=CronTrigger(
        minute="*/1", hour="8-14"), id="health-check",
        replace_existing=True)

    # Start the scheduler when the app starts
    @app.on_event("startup")
    def start_scheduler():
        logger.info('---App Scheduler is Active---')
        scheduler.start()

    # Shut down the scheduler when the app stops
    @app.on_event("shutdown")
    def stop_scheduler():
        logger.info('-*-App Scheduler is In-Active-*-')
        scheduler.shutdown()
