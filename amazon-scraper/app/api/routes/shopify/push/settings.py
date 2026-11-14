from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore
from .models import StoreSettings
from .validators import VALID_MARKUP_TYPES

router = APIRouter()

@router.post("/app/save-settings")
async def save_store_settings(settings: StoreSettings, db: Session = Depends(get_db)):
    # ✅ Store ID se dhoondein
    store = db.query(ShopifyStore).filter(ShopifyStore.id == settings.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if settings.markup_type not in VALID_MARKUP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid markup_type. Must be one of {VALID_MARKUP_TYPES}",
        )

    store.default_markup = settings.markup
    store.default_markup_type = settings.markup_type
    
    if settings.markup_type != "both":
        store.default_extra_percent = 0.0
    else:
        store.default_extra_percent = settings.extra_percent if settings.extra_percent is not None else 0.0
        
    store.default_tax_rate = settings.tax_rate if settings.tax_rate is not None else 0.0
    
    if settings.default_stock_qty is not None:
        store.default_stock_qty = int(settings.default_stock_qty)
    if settings.shopify_location_id is not None:
        store.shopify_location_id = settings.shopify_location_id

    db.commit()
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
    }