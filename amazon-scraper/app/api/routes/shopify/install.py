import asyncio
from fastapi import APIRouter, Query, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import ShopifyStore

# ✅ FIX: Imports ko aapke folder structure ke hisaab se theek kiya
from app.services.shopify_auth import (
    build_auth_url, 
    exchange_code_for_token, 
    verify_hmac,
    verify_id_token,                     # ✅ Naya import App Bridge ke liye
    exchange_id_token_for_offline_token  # ✅ Naya import Token Exchange ke liye
)
from app.services.shopify.locations import get_primary_location
from app.services.shopify.client import shopify_graphql

router = APIRouter()

FRONTEND_URL = "https://ingenious-caring-production-c9aed584.up.railway.app"

# ============================================
# 1. INSTALL ROUTE
# ============================================
@router.get("/install")
def shopify_install(shop: str = Query(...)):
    # Ensure shop domain is clean
    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"
    
    return RedirectResponse(url=build_auth_url(shop), status_code=302)


# ============================================
# 2. CALLBACK ROUTE (Custom OAuth - Legacy flow)
# ============================================
@router.get("/callback")
async def shopify_callback(
    request: Request,
    shop: str = Query(...),
    code: str = Query(...),
    hmac: str = Query(None),
    db: Session = Depends(get_db),
):
    print(f"🔄 Callback received for store: {shop}", flush=True)

    # ── 1. Verify HMAC (Security) ──
    query_params = dict(request.query_params)
    if not verify_hmac(query_params):
        print(f"❌ HMAC verification failed for {shop}", flush=True)
        return HTMLResponse(
            content="<h1>❌ Invalid Request (HMAC Failed)</h1>", 
            status_code=401
        )

    # ── 2. Exchange code for access token ──
    token_data = await exchange_code_for_token(shop, code)
    if not token_data or not token_data.get("access_token"):
        print(f"❌ Token exchange failed for {shop}", flush=True)
        return HTMLResponse(
            content="<h1>❌ Failed to get access token</h1>", 
            status_code=400
        )

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    refresh_expires_in = token_data.get("refresh_token_expires_in")
    now = datetime.now(timezone.utc)

    # ── 3. Auto-detect primary location (With Retry) ──
    location_id = None
    for attempt in range(3):
        try:
            location_id = await get_primary_location(shop, access_token)
            if location_id:
                print(f"📍 Location detected for {shop}: {location_id}", flush=True)
                break
        except Exception as e:
            print(f"⚠️ Location attempt {attempt+1} failed for {shop}: {e}", flush=True)
            await asyncio.sleep(1)

    # ── 4. Upsert ShopifyStore in DB ──
    existing = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    
    if existing:
        existing.access_token = access_token
        if refresh_token:
            existing.refresh_token = refresh_token
        if expires_in:
            existing.expires_at = now + timedelta(seconds=int(expires_in))
        if refresh_expires_in:
            existing.refresh_token_expires_at = now + timedelta(seconds=int(refresh_expires_in))
        
        if location_id:
            existing.shopify_location_id = location_id
            
        db.commit()
        print(f"✅ Existing store updated: {shop}, location_id={location_id}", flush=True)
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

    # ── 5. Redirect back to the embedded app ──
    host = request.query_params.get("host", "")
    params = f"shop={shop}"
    if host:
        params += f"&host={host}"

    redirect_url = f"{FRONTEND_URL}?{params}"
    print(f"🚀 Redirecting to frontend: {redirect_url}", flush=True)
    
    return RedirectResponse(url=redirect_url, status_code=302)


# ============================================
# 3. NAYA ROUTE: App Bridge ID Token Exchange (Managed Flow)
# ============================================
@router.post("/token-exchange")
async def token_exchange(request: Request, db: Session = Depends(get_db)):
    """
    Ye route frontend se App Bridge ka id_token leta hai,
    usko verify karta hai, aur permanent access_token bana kar
    database mein save karta hai.
    """
    data = await request.json()
    id_token = data.get("id_token")
    shop = data.get("shop")

    print(f"🔑 Token exchange request received for: {shop}", flush=True)

    # 1. ID Token verify karein (Security)
    try:
        verify_id_token(id_token) 
    except Exception as e:
        print(f"❌ ID Token verify fail: {e}", flush=True)
        raise HTTPException(status_code=401, detail="Invalid ID Token")

    # 2. ID Token ko Offline Access Token mein exchange karein
    token_data = await exchange_id_token_for_offline_token(shop, id_token)
    if not token_data or not token_data.get("access_token"):
        print(f"❌ App Bridge Token exchange failed for {shop}", flush=True)
        raise HTTPException(status_code=400, detail="Token exchange failed")

    # 3. Database mein save karein
    existing = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    now = datetime.now(timezone.utc)
    
    if existing:
        existing.access_token = token_data["access_token"]
        if token_data.get("refresh_token"): 
            existing.refresh_token = token_data["refresh_token"]
        if token_data.get("expires_in"): 
            existing.expires_at = now + timedelta(seconds=int(token_data["expires_in"]))
        db.commit()
        print(f"✅ Existing store updated via token exchange: {shop}", flush=True)
    else:
        new_store = ShopifyStore(
            shop_domain=shop,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=(now + timedelta(seconds=int(token_data["expires_in"]))) if token_data.get("expires_in") else None,
        )
        db.add(new_store)
        db.commit()
        print(f"✅ New store saved via token exchange: {shop}", flush=True)
    
    return {"status": "success"}