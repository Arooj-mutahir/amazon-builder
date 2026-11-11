import asyncio
from app.services.shopify_auth import refresh_shopify_token
from app.database import SessionLocal
from app.models import ShopifyStore

async def test():
    db = SessionLocal()
    for store in db.query(ShopifyStore).all():
        print(f"\n--- {store.shop_domain} ---")
        result = await refresh_shopify_token(store.shop_domain, store.refresh_token)
        if result and result.get("access_token"):
            token = result.get("access_token", "")
            refresh = result.get("refresh_token") or ""
            print(f"✅ SUCCESS: {token[:30]}...")
            print(f"   Expires in: {result.get('expires_in')}s")
            print(f"   New refresh: {refresh[:20]}...")
        else:
            print("❌ FAILED — refresh token bhi expired hai")

asyncio.run(test())