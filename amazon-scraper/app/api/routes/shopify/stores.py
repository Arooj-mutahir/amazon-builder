from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore

router = APIRouter()


@router.get("/stores")
def get_connected_stores(db: Session = Depends(get_db)):
    stores = db.query(ShopifyStore).all()
    return [{"id": s.id, "shop_domain": s.shop_domain} for s in stores]


@router.get("/stores/by-shop")
async def get_store_by_shop(
    shop: str = Query(..., description="Shopify shop domain, e.g. my-store.myshopify.com"),
    db: Session = Depends(get_db),
):
    """
    Returns store info (including cached location_id) for the given shop domain.
    If location_id is missing, fetches it live from Shopify and caches it.
    Frontend calls this on load with ?shop= from the URL to confirm the store is connected.
    """
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if not store:
        raise HTTPException(
            status_code=404,
            detail=f"Store '{shop}' is not connected. Please install the app first."
        )

    # ✅ Auto-populate location_id if missing (for stores connected before this feature)
    if not store.shopify_location_id:
        try:
            from app.services.shopify.locations import get_primary_location
            location_id = await get_primary_location(shop, store.access_token)
            if location_id:
                store.shopify_location_id = location_id
                db.commit()
                print(f"✅ Backfilled location_id for {shop}: {location_id}", flush=True)
        except Exception as e:
            print(f"⚠️ Could not backfill location for {shop}: {e}", flush=True)

    return {
        "id": store.id,
        "shop_domain": store.shop_domain,
        "location_id": store.shopify_location_id,
        "markup": store.default_markup or 0.0,
        "markup_type": store.default_markup_type or "fixed",
        "extra_percent": store.default_extra_percent or 0.0,
        "tax_rate": store.default_tax_rate or 0.0,
        "default_stock_qty": store.default_stock_qty or 0,
        "connected": True,
    }
