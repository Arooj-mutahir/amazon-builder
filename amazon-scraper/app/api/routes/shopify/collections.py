from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore
from app.services.shopify import fetch_all_collections
from .helpers import _get_valid_access_token

router = APIRouter()

@router.get("/collections")
async def get_all_collections(shop: str = "test-store-ispfraip.myshopify.com", db: Session = Depends(get_db)):
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if not store:
        store = db.query(ShopifyStore).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not connected")
    token = await _get_valid_access_token(store, db)
    collections = await fetch_all_collections(store.shop_domain, token)
    return {"collections": collections}