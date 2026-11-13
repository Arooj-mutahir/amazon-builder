# ============================================
# SCHEDULER JOB — Price + Stock Sync
# ============================================
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# ✅ FIX: sync_prices_job asli file (sync_job.py) se import ho raha hai
from app.worker.sync_job import sync_prices_job 
from app.api.routes.shopify.worker import run_price_update_now

scheduler = AsyncIOScheduler()


def start_scheduler():
    scheduler.add_job(
        sync_prices_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="price_sync_job",
        name="Sync Amazon Prices & Stock to Shopify",
        replace_existing=True,
    )
    scheduler.start()
    print("🚀 CRON JOB SCHEDULED: Har raat 2 baje price + stock check hoga.")