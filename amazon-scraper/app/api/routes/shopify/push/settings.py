# app/api/routes/shopify/settings.py (ya jo bhi file ho)
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore
import json

router = APIRouter()

class StoreSettings(BaseModel):
    store_id: int
    default_markup: float
    default_markup_type: str
    default_extra_percent: Optional[float] = 0.0
    default_tax_rate: Optional[float] = 0.0
    default_compare_price_markup: Optional[float] = 0.0
    default_stock_qty: Optional[int] = 100
    shopify_location_id: Optional[str] = None

VALID_MARKUP_TYPES = ["percent", "fixed", "both"]

@router.post("/app/save-settings")
async def save_store_settings(settings: StoreSettings, request: Request, db: Session = Depends(get_db)):
    # 🔥 DEBUG: Raw data check karo
    body = await request.body()
    print(f"📥 RAW PAYLOAD FROM FRONTEND: {body.decode()}", flush=True)
    print(f"📦 PARSED SETTINGS: Markup={settings.default_markup}, Type={settings.default_markup_type}, Tax={settings.default_tax_rate}", flush=True)

    store = db.query(ShopifyStore).filter(ShopifyStore.id == settings.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if settings.default_markup_type not in VALID_MARKUP_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid markup_type: {settings.default_markup_type}")

    # 🔥 DB Update
    store.default_markup = settings.default_markup
    store.default_markup_type = settings.default_markup_type
    
    if settings.default_markup_type != "both":
        store.default_extra_percent = 0.0
    else:
        store.default_extra_percent = settings.default_extra_percent or 0.0
        
    store.default_tax_rate = settings.default_tax_rate or 0.0
    store.default_compare_price_markup = settings.default_compare_price_markup or 0.0
    
    if settings.default_stock_qty is not None:
        store.default_stock_qty = int(settings.default_stock_qty)
    if settings.shopify_location_id is not None:
        store.shopify_location_id = settings.shopify_location_id

    db.commit()
    db.refresh(store)
    
    print(f"✅ DATABASE UPDATED: Markup={store.default_markup}, Type={store.default_markup_type}, Tax={store.default_tax_rate}, Compare={store.default_compare_price_markup}", flush=True)
    
    return {"success": True, "message": "Settings saved successfully!"}