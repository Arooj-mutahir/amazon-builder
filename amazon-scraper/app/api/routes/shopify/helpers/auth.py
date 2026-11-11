from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import ShopifyStore
from app.services.shopify import refresh_shopify_token

async def _get_valid_access_token(store: ShopifyStore, db: Session, force_refresh: bool = False) -> str:
    if not store.refresh_token:
        return store.access_token

    now = datetime.now(timezone.utc)
    buffer = timedelta(minutes=10)
    needs_refresh = force_refresh
    
    if not needs_refresh and store.expires_at and store.expires_at <= now + buffer:
        needs_refresh = True
        
    if needs_refresh:
        refreshed = await refresh_shopify_token(store.shop_domain, store.refresh_token)
        if refreshed and refreshed.get("access_token"):
            store.access_token = refreshed["access_token"]
            if refreshed.get("refresh_token"): store.refresh_token = refreshed["refresh_token"]
            if refreshed.get("expires_in"): store.expires_at = now + timedelta(seconds=int(refreshed["expires_in"]))
            db.commit(); db.refresh(store)
            
    return store.access_token