# app/services/shopify/webhooks_register.py (Nayi file banao)

from app.services.shopify.client import shopify_graphql
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://amazon-builder-production.up.railway.app")

async def register_webhooks(shop_domain: str, access_token: str):
    """Jab naya store install ho, toh uske liye webhooks register karo."""
    
    webhooks_to_register = [
        {
            "topic": "PRODUCTS_DELETE",
            "address": f"{BACKEND_URL}/api/shopify/app/webhooks/products-delete"
        },
        {
            "topic": "APP_UNINSTALLED",
            "address": f"{BACKEND_URL}/api/shopify/app/webhooks/app-uninstalled"
        }
    ]
    
    mutation = """
    mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
      webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
        webhookSubscription {
          id
          topic
          endpoint {
            __typename
            ... on WebhookHttpEndpoint {
              callbackUrl
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    for webhook in webhooks_to_register:
        try:
            variables = {
                "topic": webhook["topic"],
                "webhookSubscription": {
                    "callbackUrl": webhook["address"],
                    "format": "JSON"
                }
            }
            
            result = await shopify_graphql(shop_domain, access_token, mutation, variables)
            
            errors = result.get("data", {}).get("webhookSubscriptionCreate", {}).get("userErrors", [])
            if errors:
                print(f"❌ Webhook register failed for {webhook['topic']}: {errors}", flush=True)
            else:
                print(f"✅ Webhook registered: {webhook['topic']} for {shop_domain}", flush=True)
                
        except Exception as e:
            print(f"❌ Error registering webhook {webhook['topic']}: {e}", flush=True)