# refresh_all_tokens.py
import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import ShopifyStore
from app.services.shopify_auth import refresh_shopify_token

async def refresh_all():
    db = SessionLocal()
    stores = db.query(ShopifyStore).all()
    print(f"Total stores: {len(stores)}")
    
    for store in stores:
        if not store.refresh_token:
            print(f"⚠️ Skipping {store.shop_domain} - No refresh token")
            continue
            
        print(f"🔄 Refreshing token for {store.shop_domain}...")
        new_data = await refresh_shopify_token(store.shop_domain, store.refresh_token)
        
        if new_data and new_data.get("access_token"):
            store.access_token = new_data["access_token"]
            if new_data.get("refresh_token"):
                store.refresh_token = new_data["refresh_token"]
            if new_data.get("expires_in"):
                store.expires_at = datetime.utcnow() + timedelta(seconds=int(new_data["expires_in"]))
            db.commit()
            print(f"✅ Refreshed for {store.shop_domain}")
        else:
            print(f"❌ Failed for {store.shop_domain}")
    
    db.close()
    print("Done!")

if __name__ == "__main__":
    asyncio.run(refresh_all())