from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore

router = APIRouter()

class StoreSettings(BaseModel):
    store_id: int
    default_markup: Optional[float] = 0.0
    default_markup_type: Optional[str] = "fixed"
    default_extra_percent: Optional[float] = 0.0
    default_tax_rate: Optional[float] = 0.0
    default_compare_price_markup: Optional[float] = 0.0
    default_stock_qty: Optional[int] = 100
    shopify_location_id: Optional[str] = None

VALID_MARKUP_TYPES = ["percent", "fixed", "both"]

@router.post("/app/save-settings")
async def save_store_settings(settings: StoreSettings, request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    print(f"📥 RAW PAYLOAD FROM FRONTEND: {body.decode()}", flush=True)

    store = db.query(ShopifyStore).filter(ShopifyStore.id == settings.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    # 🔥 Update logic
    store.default_markup = settings.default_markup
    store.default_markup_type = settings.default_markup_type
    store.default_extra_percent = settings.default_extra_percent
    store.default_tax_rate = settings.default_tax_rate
    store.default_compare_price_markup = settings.default_compare_price_markup
    store.default_stock_qty = settings.default_stock_qty

    if settings.shopify_location_id is not None:
        store.shopify_location_id = settings.shopify_location_id

    try:
        db.commit()
        db.refresh(store)
        print(f"✅ DB UPDATED: Markup={store.default_markup}, Tax={store.default_tax_rate}, Compare={store.default_compare_price_markup}", flush=True)
    except Exception as e:
        db.rollback()
        print(f"❌ DB COMMIT FAILED: {e}", flush=True)
        raise HTTPException(status_code=500, detail=f"DB Commit Failed: {str(e)}")

    return {"success": True, "message": "Settings saved successfully!"}