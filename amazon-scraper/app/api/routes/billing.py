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

# 🔥 Helper: Shop domain se store fetch karo
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

    # 🔥 IMPORTANT: Callback URL (Bina charge_id ke, kyunki wo abhi generate nahi hui)
    # Shopify jab return_url par bhejega, toh wo automatically URL mein 
    # charge_id add kar dega (GraphQL API ka feature hai).
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
    charge_id: str = Query(None), # Shopify charge_id bhejta hai (agar success ho)
    shop: str = Query(...), 
    db: Session = Depends(get_db)
):
    print(f"🔙 Billing callback received for {shop} | Charge ID: {charge_id}", flush=True)
    
    # Agar user ne payment cancel kar diya aur charge_id nahi aayi
    if not charge_id:
        print("⚠️ No charge_id found in callback URL. User may have cancelled.", flush=True)
        frontend_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/amazon-scraper-and-manager/billing?error=cancelled"
        return RedirectResponse(url=frontend_url)

    store = get_store_by_shop(shop, db)

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
    result = await shopify_graphql(store.shop_domain, store.access_token, query, {"id": charge_id})
    node = result.get("data", {}).get("node", {})
    
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