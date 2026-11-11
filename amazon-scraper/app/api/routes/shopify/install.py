from fastapi import APIRouter, Query, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import ShopifyStore
from app.services.shopify import build_auth_url, exchange_code_for_token

router = APIRouter()

@router.get("/install")
def shopify_install(shop: str = Query(...)):
    return RedirectResponse(url=build_auth_url(shop))

@router.get("/callback")
async def shopify_callback(request: Request, shop: str = Query(...), code: str = Query(...), hmac: str = Query(None), db: Session = Depends(get_db)):
    # Ye function ab sahi token fetch karega
    token_data = await exchange_code_for_token(shop, code)
    if not token_data or not token_data.get("access_token"):
        return HTMLResponse(content="<h1>❌ Failed to get access token</h1>", status_code=400)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    refresh_expires_in = token_data.get("refresh_token_expires_in")
    now = datetime.now(timezone.utc)

    existing = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if existing:
        existing.access_token = access_token
        if refresh_token: existing.refresh_token = refresh_token
        if expires_in: existing.expires_at = now + timedelta(seconds=int(expires_in))
        if refresh_expires_in: existing.refresh_token_expires_at = now + timedelta(seconds=int(refresh_expires_in))
        db.commit()
    else:
        db.add(ShopifyStore(
            shop_domain=shop, access_token=access_token, refresh_token=refresh_token,
            expires_at=(now + timedelta(seconds=int(expires_in))) if expires_in else None,
            refresh_token_expires_at=(now + timedelta(seconds=int(refresh_expires_in))) if refresh_expires_in else None,
        ))
        db.commit()
    return HTMLResponse(content="<h1>✅ Installed Successfully! You can close this tab.</h1>")