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


# 🔥 NAYA FUNCTION: Manual Trigger ke liye
async def run_price_update_now():
    """
    Dashboard ke 'Manual Sync' button se trigger hota hai.
    Agar specific store_id diya hai, toh sirf usi store ka sync karega.
    Agar None hai, toh saare eligible stores ka sync karega.
    """
    print("🚀 [MANUAL SYNC] Triggered manually from dashboard.", flush=True)
    await sync_prices_job(store_id=None)


def start_scheduler():
    scheduler.add_job(
        _downgrade_expired_stores,  # ✅ Pehle expiry check karein
        trigger=CronTrigger(hour=2, minute=0),
        id="expiry_check_job",
        name="Downgrade Expired Stores",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_prices_job,
        trigger=CronTrigger(hour=2, minute=5), # ✅ Expiry check ke 5 min baad sync
        id="price_sync_job",
        name="Sync Amazon Prices & Stock to Shopify (Advance plan only)",
        replace_existing=True,
    )
    scheduler.start()
    print("🚀 CRON JOB SCHEDULED: Har raat 2 baje (advance plan stores only) price + stock sync hoga.")