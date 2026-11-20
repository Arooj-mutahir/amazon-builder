# app/services/scheduler.py
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models import ShopifyStore
from app.worker.sync_job import sync_prices_job

scheduler = AsyncIOScheduler()


def _downgrade_expired_stores():
    """Har cron se pehle expiry check — expired advance stores ko basic pe le aao."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(ShopifyStore).filter(
            ShopifyStore.plan == "advance",
            ShopifyStore.plan_expires_at.isnot(None),
            ShopifyStore.plan_expires_at < now,
        ).all()

        for store in expired:
            print(f"⏰ [EXPIRY] {store.shop_domain} expired → downgrading to basic", flush=True)
            store.plan = "basic"
            store.plan_status = "expired"
            store.auto_sync_enabled = False

        if expired:
            db.commit()
            print(f"✅ {len(expired)} store(s) downgraded due to expiry.", flush=True)
    except Exception as e:
        print(f"❌ Expiry check failed: {e}", flush=True)
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(
        sync_prices_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="price_sync_job",
        name="Sync Amazon Prices & Stock to Shopify (Advance plan only)",
        replace_existing=True,
    )
    scheduler.start()
    print("🚀 CRON JOB SCHEDULED: Har raat 2 baje (advance plan stores only) price + stock sync hoga.")