from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import ShopifyStore
from app.services.shopify import build_auth_url, exchange_code_for_token
from app.services.shopify.locations import get_primary_location
from app.services.shopify.client import shopify_graphql

router = APIRouter()

@router.get("/install")
def shopify_install(shop: str = Query(...)):
    return RedirectResponse(url=build_auth_url(shop))


@router.get("/callback")
async def shopify_callback(
    request: Request,
    shop: str = Query(...),
    code: str = Query(...),
    hmac: str = Query(None),
    db: Session = Depends(get_db),
):
    # ── 1. Exchange code for access token ──
    token_data = await exchange_code_for_token(shop, code)
    if not token_data or not token_data.get("access_token"):
        return HTMLResponse(content="<h1>❌ Failed to get access token</h1>", status_code=400)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    refresh_expires_in = token_data.get("refresh_token_expires_in")
    now = datetime.now(timezone.utc)

    # ── 2. Auto-detect primary location from Shopify GraphQL ──
    location_id = None
    try:
        location_id = await get_primary_location(shop, access_token)
        print(f"📍 Auto-detected location for {shop}: {location_id}", flush=True)
    except Exception as e:
        print(f"⚠️ Could not fetch location for {shop}: {e}", flush=True)

    # ── 3. Upsert ShopifyStore in DB (save location_id) ──
    existing = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if existing:
        existing.access_token = access_token
        if refresh_token:
            existing.refresh_token = refresh_token
        if expires_in:
            existing.expires_at = now + timedelta(seconds=int(expires_in))
        if refresh_expires_in:
            existing.refresh_token_expires_at = now + timedelta(seconds=int(refresh_expires_in))
        # Always update location_id if we got one
        if location_id:
            existing.shopify_location_id = location_id
            print(f"✅ Updated location_id for existing store {shop}: {location_id}", flush=True)
        db.commit()
    else:
        new_store = ShopifyStore(
            shop_domain=shop,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=(now + timedelta(seconds=int(expires_in))) if expires_in else None,
            refresh_token_expires_at=(now + timedelta(seconds=int(refresh_expires_in))) if refresh_expires_in else None,
            shopify_location_id=location_id,
        )
        db.add(new_store)
        db.commit()
        print(f"✅ New store saved: {shop}, location_id={location_id}", flush=True)

    # ── 4. Redirect back to the embedded app ──
    return RedirectResponse(url="https://ingenious-caring-production-c9aed584.up.railway.app")
