from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore, Product

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
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
    if not store:
        raise HTTPException(
            status_code=404,
            detail=f"Store '{shop}' is not connected. Please install the app first."
        )

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


@router.get("/dashboard-stats")
def get_dashboard_stats(
    store_id: int = Query(None, description="Filter by store ID"),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Product)
        if store_id:
            query = query.filter(Product.shopify_store_id == store_id)

        total_products = query.count()
        active_products = query.filter(Product.shopify_product_id.isnot(None)).count()
        out_of_stock = query.filter(Product.is_available == False).count()
        recent_products = query.order_by(Product.id.desc()).limit(5).all()

        recent_data = []
        for p in recent_products:
            recent_data.append({
                "id": p.id,
                "title": p.title or "Untitled",
                "asin": p.asin or "",
                "price": float(p.price) if p.price else 0.0,
                "is_available": bool(p.is_available),
            })

        return {
            "total_products": total_products,
            "active_products": active_products,
            "out_of_stock": out_of_stock,
            "recent_products": recent_data
        }
    except Exception as e:
        print(f"❌ Error fetching dashboard stats: {e}", flush=True)
        return {
            "total_products": 0,
            "active_products": 0,
            "out_of_stock": 0,
            "recent_products": []
        }


# ============================================
# ✅ NAYA: Saare Products Fetch Karne Ka Endpoint
# ============================================
@router.get("/products")
def get_all_products(
    store_id: int = Query(None, description="Filter by store ID"),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(Product)
        if store_id:
            query = query.filter(Product.shopify_store_id == store_id)

        # Saare products fetch karein (Latest pehle)
        products = query.order_by(Product.id.desc()).all()

        products_data = []
        for p in products:
            products_data.append({
                "id": p.id,
                "title": p.title or "Untitled",
                "asin": p.asin or "",
                "amazon_price": float(p.amazon_price) if getattr(p, 'amazon_price', None) else (float(p.price) if p.price else 0.0),
                "shopify_price": float(p.price) if p.price else 0.0,
                "stock": p.stock_quantity if getattr(p, 'stock_quantity', None) else (10 if p.is_available else 0),
                "is_available": bool(p.is_available),
                "status": "Active" if p.is_available else "Out of Stock",
                "image": getattr(p, 'image_url', None),
                "auto_sync": True 
            })

        return products_data

    except Exception as e:
        print(f"❌ Error fetching all products: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Failed to fetch products")