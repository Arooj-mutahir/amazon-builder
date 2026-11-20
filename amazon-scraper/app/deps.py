# app/deps.py
from datetime import datetime
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.product import ShopifyStore
from app.plan_config import has_feature


def _auto_expire(store: ShopifyStore, db: Session):
    """Expired plan → basic pe auto-downgrade (cron nahi chal raha tab bhi)."""
    if store.plan_expires_at and store.plan_expires_at < datetime.utcnow():
        if store.plan != "basic" or store.plan_status != "expired":
            store.plan = "basic"
            store.plan_status = "expired"
            store.auto_sync_enabled = False
            db.commit()
            db.refresh(store)
    return store


def get_current_store(request: Request, db: Session = Depends(get_db)) -> ShopifyStore:
    """
    Store identify karta hai. Yahan tum apna auth tarika plug karo:
    - JWT se store_id
    - ya Shopify OAuth session
    - ya shop domain header (X-Shop-Domain)
    """
    # 👇 Example 1: JWT/session se store_id (recommended)
    # store_id = request.state.store_id

    # 👇 Example 2: shop domain header (dev/testing ke liye)
    shop_domain = request.headers.get("X-Shop-Domain")
    if shop_domain:
        store = db.query(ShopifyStore).filter(
            ShopifyStore.shop_domain == shop_domain
        ).first()
    else:
        # fallback — single-store setup
        store = db.query(ShopifyStore).first()

    if not store:
        raise HTTPException(status_code=401, detail="Store not found / not authenticated")

    return _auto_expire(store, db)


def require_feature(feature: str):
    """Route dependency: @router.post(..., dependencies=[Depends(require_feature('manual_sync'))])"""
    def checker(store: ShopifyStore = Depends(get_current_store)):
        if not has_feature(store, feature):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "plan_upgrade_required",
                    "message": f"'{feature}' feature sirf Advance plan mein available hai.",
                    "current_plan": store.plan,
                    "upgrade_url": "/billing/upgrade",
                },
            )
        return store
    return checker