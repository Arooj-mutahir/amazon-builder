# app/api/routes/shopify/token_exchange.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.database import get_db
from app.models import ShopifyStore
from app.services.shopify_auth import verify_id_token, exchange_id_token_for_offline_token

router = APIRouter()

class TokenExchangeRequest(BaseModel):
    shop: str
    id_token: str

@router.post("/token-exchange")
async def token_exchange(payload: TokenExchangeRequest, db: Session = Depends(get_db)):
    try:
        # 1. ID token verify karein
        verify_id_token(payload.id_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    # 2. Shopify se offline access token exchange karein
    token_data = await exchange_id_token_for_offline_token(payload.shop, payload.id_token)
    
    if not token_data or not token_data.get("access_token"):
        raise HTTPException(status_code=400, detail="Shopify token exchange failed")

    # 3. Database mein save ya update karein
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == payload.shop).first()
    
    if store:
        store.access_token = token_data["access_token"]
        store.refresh_token = token_data.get("refresh_token")
        if token_data.get("expires_in"):
            store.expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
    else:
        store = ShopifyStore(
            shop_domain=payload.shop,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=(datetime.utcnow() + timedelta(seconds=token_data["expires_in"])) if token_data.get("expires_in") else None
        )
        db.add(store)
        
    db.commit()
    db.refresh(store)
    
    return {"success": True, "store_id": store.id, "shop_domain": store.shop_domain}