from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore
from app.services.shopify import fetch_all_collections
from .helpers import _get_valid_access_token

router = APIRouter()

@router.get("/collections")
async def get_all_collections(shop: Optional[str] = Query(None), db: Session = Depends(get_db)):
    # Agar shop URL bheja gaya hai toh woh uthayein, warna pehla connected store uthayein
    if shop:
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    else:
        store = db.query(ShopifyStore).first()
        
    if not store:
        raise HTTPException(status_code=404, detail="No store connected. Please install the app first.")
        
    token = await _get_valid_access_token(store, db)
    collections = await fetch_all_collections(store.shop_domain, token)
    return {"collections": collections}