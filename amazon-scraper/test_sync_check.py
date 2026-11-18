# test_sync_check.py
from app.database import SessionLocal
from app.models import ShopifyStore
import asyncio

async def test_cron_logic():
    print("🚀 Starting Cron Job Test...")
    db = SessionLocal()
    
    try:
        stores = db.query(ShopifyStore).all()
        
        for store in stores:
            # ✅ YAHAN WO CHECK HAI JO CRON JOB MEIN HONA CHAHIYE
            if not store.auto_sync_enabled:
                print(f"⏸️ SKIPPED: {store.shop_domain} (Auto-Sync is OFF)")
                continue  # Skip this store
            
            # Agar enabled hai, toh yeh print karega
            print(f"🔄 RUNNING: {store.shop_domain} (Auto-Sync is ON) -> Will scrape Amazon...")
            
            # (Actual scraper code yahan aayega, hum abhi test kar rahe hain)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_cron_logic())