# app/dependencies.py
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore


def get_store_or_404(
    store_id: int = Query(..., description="Store ID"),
    db: Session = Depends(get_db),
) -> ShopifyStore:
    """
    Fetch store by store_id. Raises 404 if not found.
    """
    store = db.query(ShopifyStore).filter(ShopifyStore.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    return store


def require_advance_plan(
    store: ShopifyStore = Depends(get_store_or_404),
) -> ShopifyStore:
    """
    Allow only Advance plan stores. Raises 403 otherwise.
    Case-insensitive check to handle 'Advance', 'ADVANCE', 'advance ' etc.
    """
    if (store.plan or "").strip().lower() != "advance":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature is available only on the Advance plan. Please upgrade.",
        )
    return store