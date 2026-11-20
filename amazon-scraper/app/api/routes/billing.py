# app/api/routes/billing.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_store
from app.models.product import ShopifyStore
from app.plan_config import get_plan_snapshot

router = APIRouter(tags=["billing"])


@router.get("/status")
def plan_status(store: ShopifyStore = Depends(get_current_store)):
    return get_plan_snapshot(store)


@router.post("/upgrade")
def upgrade(
    store: ShopifyStore = Depends(get_current_store),
    db: Session = Depends(get_db),
):
    if store.plan == "advance" and store.plan_status == "active":
        raise HTTPException(400, "Already on Advance plan")

    store.plan = "advance"
    store.plan_status = "active"
    store.plan_started_at = datetime.utcnow()
    store.plan_expires_at = datetime.utcnow() + timedelta(days=30)
    store.auto_sync_enabled = True
    db.commit()
    db.refresh(store)
    return {"status": "upgraded", **get_plan_snapshot(store)}


@router.post("/downgrade")
def downgrade(
    store: ShopifyStore = Depends(get_current_store),
    db: Session = Depends(get_db),
):
    if store.plan == "basic":
        raise HTTPException(400, "Already on Basic plan")

    store.plan = "basic"
    store.plan_status = "active"
    store.auto_sync_enabled = False
    store.plan_expires_at = None
    db.commit()
    db.refresh(store)
    return {"status": "downgraded", **get_plan_snapshot(store)}