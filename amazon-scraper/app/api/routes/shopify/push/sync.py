# app/api/routes/shopify/push/sync.py

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ShopifyStore
from app.services.scheduler import run_price_update_now
from app.worker.sync_job import sync_prices_job

router = APIRouter()

# ==========================================
# 1. Manual Sync (Poora Store)
# ==========================================
@router.post("/sync-prices")
async def sync_prices_manually(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_price_update_now)
    return {"success": True, "message": "Price + stock sync started in background. Check terminal!"}

# ==========================================
# 2. Single Product Sync (Table ke Sync button ke liye)
# ==========================================
class SyncSingleRequest(BaseModel):
    store_id: int
    asin: str
    product_id: int

@router.post("/app/sync-single-product")
async def sync_single_product(payload: SyncSingleRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # 1. Store check karein
    store = db.query(ShopifyStore).filter(ShopifyStore.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found.")
    
    # (Optional) Advance plan check
    if store.plan != "advance":
        raise HTTPException(status_code=403, detail="Manual Sync is only for Advance Plan.")

    # 2. Product check karein
    product = db.query(Product).filter(
        Product.id == payload.product_id, 
        Product.shopify_store_id == payload.store_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this store.")

    # 3. Background task mein sync shuru karein
    # Abhi ke liye hum poore store ka sync trigger kar rahe hain.
    # Agar aap chahte hain ki sirf yahi product sync ho, toh sync_job.py mein 
    # product_id pass karne ka option add karna hoga.
    background_tasks.add_task(sync_prices_job, store_id=payload.store_id)
    
    return {"success": True, "message": f"Sync started for ASIN {payload.asin}. Check terminal for updates."}