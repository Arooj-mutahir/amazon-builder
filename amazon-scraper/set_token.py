import asyncio
import httpx
import os
from dotenv import load_dotenv

# .env file load karein
load_dotenv()

from app.database import SessionLocal
from app.models import ShopifyStore

# Token aur Shop .env file se aayenge
NEW_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP = os.getenv("SHOPIFY_SHOP_DOMAIN")

async def verify_token():
    """Shopify API call karke token valid hai ya nahi check karo."""
    if not NEW_TOKEN or not SHOP:
        print("❌ Error: .env file mein SHOPIFY_ACCESS_TOKEN ya SHOPIFY_SHOP_DOMAIN missing hai!")
        return False

    url = f"https://{SHOP}/admin/api/2024-04/graphql.json"
    headers = {
        "X-Shopify-Access-Token": NEW_TOKEN,
        "Content-Type": "application/json",
    }
    query = """
    query {
      shop {
        name
        myshopifyDomain
        currencyCode
      }
    }
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json={"query": query}, headers=headers)
            if r.status_code == 200:
                data = r.json()
                shop_info = (data.get("data") or {}).get("shop") or {}
                if shop_info.get("name"):
                    print(f"✅ Token VALID!")
                    print(f"   Shop name: {shop_info['name']}")
                    print(f"   Domain: {shop_info['myshopifyDomain']}")
                    print(f"   Currency: {shop_info['currencyCode']}")
                    return True
            print(f"❌ Token INVALID — status: {r.status_code}")
            print(f"   Response: {r.text[:300]}")
            return False
    except Exception as e:
        print(f"❌ Token check failed: {e}")
        return False


async def save_token():
    """Token verify hone ke baad DB mein save karo."""
    is_valid = await verify_token()
    if not is_valid:
        print("\n⚠️  Token invalid hai — DB mein save nahi kiya")
        return

    print("\n💾 Saving to DB...")
    db = SessionLocal()

    store = db.query(ShopifyStore).filter(
        ShopifyStore.shop_domain == SHOP
    ).first()

    if store:
        store.access_token = NEW_TOKEN
        store.expires_at = None
        store.refresh_token = None
        store.refresh_token_expires_at = None
        db.commit()
        print(f"✅ Updated existing store: {SHOP}")
    else:
        new_store = ShopifyStore(
            shop_domain=SHOP,
            access_token=NEW_TOKEN,
            refresh_token=None,
            expires_at=None,
            refresh_token_expires_at=None,
        )
        db.add(new_store)
        db.commit()
        print(f"✅ Created new store: {SHOP}")

    # Verify from DB
    store = db.query(ShopifyStore).filter(
        ShopifyStore.shop_domain == SHOP
    ).first()
    print(f"\n📋 DB confirmation:")
    print(f"   Shop: {store.shop_domain}")
    print(f"   Token: {store.access_token[:30]}...")
    print(f"   Expires: {store.expires_at}")
    print(f"   Refresh token: {store.refresh_token}")
    db.close()


if __name__ == "__main__":
    asyncio.run(save_token())