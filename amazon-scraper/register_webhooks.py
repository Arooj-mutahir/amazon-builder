# register_webhooks.py
import asyncio
from app.database import SessionLocal
from app.models import ShopifyStore
from app.services.shopify.client import shopify_graphql

BACKEND_URL = "https://amazon-builder-production.up.railway.app"

async def main():
    db = SessionLocal()
    try:
        stores = db.query(ShopifyStore).filter(ShopifyStore.access_token.isnot(None)).all()
        print(f"🔄 Found {len(stores)} stores to register webhooks for.", flush=True)
        
        webhooks_to_register = [
            {"topic": "PRODUCTS_DELETE", "address": f"{BACKEND_URL}/api/shopify/app/webhooks/products-delete"},
            {"topic": "APP_UNINSTALLED", "address": f"{BACKEND_URL}/api/shopify/app/webhooks/app-uninstalled"}
        ]

        webhook_mutation = """
        mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
          webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
            webhookSubscription { id }
            userErrors { field message }
          }
        }
        """

        for store in stores:
            print(f"\n🔄 Registering for {store.shop_domain}...", flush=True)
            for webhook in webhooks_to_register:
                try:
                    variables = {
                        "topic": webhook["topic"],
                        "webhookSubscription": {
                            "callbackUrl": webhook["address"],
                            "format": "JSON"
                        }
                    }
                    res = await shopify_graphql(store.shop_domain, store.access_token, webhook_mutation, variables)
                    if res and "errors" in res:
                        print(f"  ⚠️ {webhook['topic']}: {res['errors']}", flush=True)
                    else:
                        user_errors = res.get("data", {}).get("webhookSubscriptionCreate", {}).get("userErrors", [])
                        if user_errors:
                            print(f"  ⚠️ {webhook['topic']}: {user_errors}", flush=True)
                        else:
                            print(f"  ✅ {webhook['topic']} registered", flush=True)
                except Exception as e:
                    print(f"  ❌ {webhook['topic']} error: {e}", flush=True)
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())