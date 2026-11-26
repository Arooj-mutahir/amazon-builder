from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore

router = APIRouter()

# 🔥 NAYA MODEL (default_ prefix ke saath)
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
async def save_store_settings(settings: StoreSettings, db: Session = Depends(get_db)):
    # ✅ Store ID se dhoondein
    store = db.query(ShopifyStore).filter(ShopifyStore.id == settings.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if settings.default_markup_type not in VALID_MARKUP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid markup_type. Must be one of {VALID_MARKUP_TYPES}",
        )

    # 🔥 YAHAN FIX: settings.default_markup use karo
    store.default_markup = settings.default_markup
    store.default_markup_type = settings.default_markup_type
    
    if settings.default_markup_type != "both":
        store.default_extra_percent = 0.0
    else:
        store.default_extra_percent = settings.default_extra_percent if settings.default_extra_percent is not None else 0.0
        
    store.default_tax_rate = settings.default_tax_rate if settings.default_tax_rate is not None else 0.0
    store.default_compare_price_markup = settings.default_compare_price_markup if settings.default_compare_price_markup is not None else 0.0
    
    if settings.default_stock_qty is not None:
        store.default_stock_qty = int(settings.default_stock_qty)
    if settings.shopify_location_id is not None:
        store.shopify_location_id = settings.shopify_location_id

    db.commit()
    
    print(f"✅ Settings saved: Markup={store.default_markup}, Type={store.default_markup_type}, Tax={store.default_tax_rate}, Compare={store.default_compare_price_markup}", flush=True)
    
    return {"success": True, "message": "Settings saved successfully!"}


@router.get("/app/store-settings/{shop_domain}")
async def get_store_settings(shop_domain: str, db: Session = Depends(get_db)):
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop_domain).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return {
        "shop_domain": store.shop_domain,
        "markup": store.default_markup,
        "markup_type": store.default_markup_type,
        "extra_percent": store.default_extra_percent or 0.0,
        "tax_rate": store.default_tax_rate or 0.0,
        "default_stock_qty": store.default_stock_qty or 0,
        "shopify_location_id": store.shopify_location_id,
        "compare_price_markup": store.default_compare_price_markup or 0.0,
    }