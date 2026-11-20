# app/api/routes/billing.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.product import ShopifyStore
from app.plan_config import get_plan_snapshot
from app.services.shopify.client import shopify_graphql

router = APIRouter(tags=["billing"])

def get_store_by_shop(shop: str, db: Session):
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if not store:
        raise HTTPException(404, f"Store '{shop}' not found")
    return store

@router.get("/status")
def plan_status(
    shop: str = Query(...),
    db: Session = Depends(get_db)
):
    store = get_store_by_shop(shop, db)
    return get_plan_snapshot(store)

@router.post("/upgrade")
async def upgrade(
    shop: str = Query(...),
    db: Session = Depends(get_db)
):
    store = get_store_by_shop(shop, db)

    if store.plan == "advance" and store.plan_status == "active":
        raise HTTPException(400, "Already on Advance plan")

    return_url = f"https://amazon-builder-production.up.railway.app/api/shopify/billing/callback?shop={shop}"

    mutation = """
    mutation CreateSubscription($name: String!, $returnUrl: URL!, $test: Boolean, $lineItems: [AppSubscriptionLineItemInput!]!) {
      appSubscriptionCreate(name: $name, returnUrl: $returnUrl, test: $test, lineItems: $lineItems) {
        confirmationUrl
        userErrors { field message }
      }
    }
    """
    
    variables = {
        "name": "Advance Plan",
        "returnUrl": return_url,
        "test": True,
        "lineItems": [{
            "plan": {
                "appRecurringPricingDetails": {
                    "price": {"amount": 19.99, "currencyCode": "USD"},
                    "interval": "EVERY_30_DAYS"
                }
            }
        }]
    }

    print(f"📤 Sending upgrade request for {shop}...", flush=True)
    result = await shopify_graphql(store.shop_domain, store.access_token, mutation, variables)
    print(f"📥 Shopify Billing Response: {result}", flush=True)
    
    if "errors" in result or result.get("data", {}).get("appSubscriptionCreate", {}).get("userErrors"):
        raise HTTPException(status_code=400, detail=str(result))

    confirmation_url = result["data"]["appSubscriptionCreate"]["confirmationUrl"]
    return {"confirmation_url": confirmation_url}

@router.get("/callback")
async def billing_callback(
    charge_id: str = Query(None),
    shop: str = Query(...), 
    db: Session = Depends(get_db)
):
    print(f"🔙 Billing callback received for {shop} | Charge ID: {charge_id}", flush=True)
    
    if not charge_id:
        print("⚠️ No charge_id found in callback URL.", flush=True)
        frontend_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/amazon-scraper-and-manager/billing?error=cancelled"
        return RedirectResponse(url=frontend_url)

    try:
        store = get_store_by_shop(shop, db)
        
        # 🔥 FIX: Shopify charge_id ko GID format mein convert karo
        # Charge_id aata hai simple number (74227712077), usko GID banado
        gid = f"gid://shopify/AppSubscription/{charge_id}"
        print(f"🔍 Querying Shopify with GID: {gid}", flush=True)

        query = """
        query getSubscription($id: ID!) {
          node(id: $id) {
            ... on AppSubscription {
              id
              status
            }
          }
        }
        """
        result = await shopify_graphql(store.shop_domain, store.access_token, query, {"id": gid})
        print(f"📥 Shopify Subscription Verify Response: {result}", flush=True)
        
        node = result.get("data", {}).get("node", {})
        if not node:
            # Fallback: Query AppSubscription directly if node is null
            print(f"⚠️ Node null, trying direct query...", flush=True)
            query2 = """
            query getAppSubscription($id: ID!) {
              appSubscription(id: $id) {
                id
                status
              }
            }
            """
            result = await shopify_graphql(store.shop_domain, store.access_token, query2, {"id": gid})
            print(f"📥 Fallback Response: {result}", flush=True)
            node = result.get("data", {}).get("appSubscription", {})
        
        if node.get("status") == "ACTIVE":
            print(f"✅ Charge ACTIVE! Upgrading store {shop} to Advance.", flush=True)
            store.plan = "advance"
            store.plan_status = "active"
            store.plan_started_at = datetime.utcnow()
            store.plan_expires_at = datetime.utcnow() + timedelta(days=30)
            store.auto_sync_enabled = True
            db.commit()
            frontend_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/amazon-scraper-and-manager/billing?success=true"
        else:
            print(f"❌ Charge NOT ACTIVE. Status: {node.get('status')}", flush=True)
            frontend_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/amazon-scraper-and-manager/billing?error=failed"
            
    except Exception as e:
        print(f"❌ Callback Error: {e}", flush=True)
        db.rollback()
        frontend_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/amazon-scraper-and-manager/billing?error=server_error"

    return RedirectResponse(url=frontend_url)

@router.post("/downgrade")
def downgrade(
    shop: str = Query(...),
    db: Session = Depends(get_db)
):
    store = get_store_by_shop(shop, db)

    if store.plan == "basic":
        raise HTTPException(400, "Already on Basic plan")

    store.plan = "basic"
    store.plan_status = "active"
    store.auto_sync_enabled = False
    store.plan_expires_at = None
    db.commit()
    db.refresh(store)
    return {"status": "downgraded", **get_plan_snapshot(store)}