from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore

router = APIRouter()

class StoreSettings(BaseModel):
    store_id: int
    default_markup: Optional[float] = None
    default_markup_type: Optional[str] = None
    default_extra_percent: Optional[float] = None
    default_tax_rate: Optional[float] = None
    default_compare_price_markup: Optional[float] = None
    default_stock_qty: Optional[int] = None
    shopify_location_id: Optional[str] = None
    
    # 🔥 Purane field names bhi accept karo (fallback)
    markup: Optional[float] = None
    markup_type: Optional[str] = None
    extra_percent: Optional[float] = None
    tax_rate: Optional[float] = None
    compare_price_markup: Optional[float] = None

VALID_MARKUP_TYPES = ["percent", "fixed", "both"]

@router.post("/app/save-settings")
async def save_store_settings(settings: StoreSettings, request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    print(f"📥 RAW PAYLOAD: {body.decode()}", flush=True)

    store = db.query(ShopifyStore).filter(ShopifyStore.id == settings.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # 🔥 SMART FALLBACK: Jo available ho woh use karo
    final_markup = settings.default_markup if settings.default_markup is not None else (settings.markup or 0.0)
    final_markup_type = settings.default_markup_type if settings.default_markup_type is not None else (settings.markup_type or "fixed")
    final_extra = settings.default_extra_percent if settings.default_extra_percent is not None else (settings.extra_percent or 0.0)
    final_tax = settings.default_tax_rate if settings.default_tax_rate is not None else (settings.tax_rate or 0.0)
    final_compare = settings.default_compare_price_markup if settings.default_compare_price_markup is not None else (settings.compare_price_markup or 0.0)

    if final_markup_type not in VALID_MARKUP_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid markup_type: {final_markup_type}")

    # DB Update
    store.default_markup = final_markup
    store.default_markup_type = final_markup_type
    store.default_extra_percent = final_extra if final_markup_type == "both" else 0.0
    store.default_tax_rate = final_tax
    store.default_compare_price_markup = final_compare
    
    if settings.default_stock_qty is not None:
        store.default_stock_qty = int(settings.default_stock_qty)
    if settings.shopify_location_id is not None:
        store.shopify_location_id = settings.shopify_location_id

    try:
        db.commit()
        db.refresh(store)
        print(f"✅ DB UPDATED: Markup={store.default_markup}, Type={store.default_markup_type}, Tax={store.default_tax_rate}, Compare={store.default_compare_price_markup}", flush=True)
    except Exception as e:
        db.rollback()
        print(f"❌ DB COMMIT FAILED: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"DB Commit Failed: {str(e)}")

    return {"success": True, "message": "Settings saved successfully!"}