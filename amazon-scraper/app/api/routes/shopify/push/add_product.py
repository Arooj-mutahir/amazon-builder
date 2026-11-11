from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models import ShopifyStore
from app.api.routes.shopify.helpers import _normalize_amazon_url, extract_asin_from_url
from app.api.routes.shopify.worker import _background_fetch_and_push
from .validators import VALID_MARKUP_TYPES, clean_markup_values

router = APIRouter()

@router.post("/app/add-product")
async def add_product_from_shopify_app(
    background_tasks: BackgroundTasks,
    amazon_url: str = Body(..., embed=True),
    shop_domain: str = Body(..., embed=True),
    markup: Optional[float] = Body(0.0, embed=True),
    markup_type: Optional[str] = Body("fixed", embed=True),
    extra_percent: Optional[float] = Body(0.0, embed=True),
    tax_rate: Optional[float] = Body(0.0, embed=True),
    collection_ids: list = Body(default=[], embed=True),
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    # ✅ Validate and clean
    markup, markup_type, extra_percent, tax_rate = clean_markup_values(markup, markup_type, extra_percent, tax_rate)

    # 🔥 DEBUG PRINT
    print(f"\n📥 FRONTEND SE AAYA: Markup={markup}, Type={markup_type}, Extra={extra_percent}, Tax={tax_rate}", flush=True)

    amazon_url = _normalize_amazon_url(amazon_url)
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop_domain).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not connected")

    asin_quick = extract_asin_from_url(amazon_url)
    if not asin_quick:
        raise HTTPException(status_code=400, detail="Invalid Amazon URL — ASIN not found")

    if markup_type not in VALID_MARKUP_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid markup_type. Must be one of {VALID_MARKUP_TYPES}",
        )

    background_tasks.add_task(
        _background_fetch_and_push,
        amazon_url=amazon_url, shop_domain=shop_domain, store_id=store.id,
        markup=markup, markup_type=markup_type, extra_percent=extra_percent,
        tax_rate=tax_rate,
        collection_ids=collection_ids or [],
    )
    return {"success": True, "message": "Fetch started.", "asin": asin_quick}