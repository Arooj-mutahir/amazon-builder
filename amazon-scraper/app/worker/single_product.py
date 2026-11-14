# app/worker/single_product.py
import traceback
from app.database import SessionLocal
from app.models import Product, ShopifyStore
from app.services.shopify import create_shopify_product, publish_product, set_product_metafields_smart
from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token
from app.worker.stock_utils import _get_availability, _resolve_stock

async def process_single_variant(
    store, main_data, user_markup, user_markup_type, user_extra, user_tax, 
    final_tags, extracted_categories, shopify_payload, shop_domain, db, default_stock_qty,
    compare_price_markup: float = 0.0  # ✅ NAYA PARAMETER
):
    new_product = None
    existing = db.query(Product).filter(Product.asin == main_data["asin"]).first()
    
    parent_available = _get_availability(main_data)
    parent_stock_raw = main_data.get("stock_qty")
    parent_stock_qty = _resolve_stock(parent_available, parent_stock_raw, default_stock_qty)
    parent_in_stock = bool(parent_available) if parent_stock_qty is not None else False
    parent_stock = parent_stock_qty or 0
    availability_str = "In Stock" if parent_in_stock else "Out of Stock"

    if existing:
        new_product = existing
        new_product.shopify_store_id = store.id
        new_product.shopify_status = "active"
        new_product.price = shopify_payload["price"]
        new_product.amazon_price = main_data.get("price")
        new_product.title = main_data.get("title")
        new_product.brand = main_data.get("brand")
        new_product.description = main_data.get("description", "")
        new_product.image_url = (main_data.get("images") or [None])[0]
        new_product.images = main_data.get("images") or []
        new_product.rating = main_data.get("rating")
        new_product.reviews_count = main_data.get("reviews_count")
        new_product.availability = availability_str
        new_product.is_available = parent_in_stock
        new_product.stock_quantity = parent_stock
        new_product.markup = user_markup
        new_product.markup_type = user_markup_type
        new_product.extra_percent = user_extra
        new_product.tax_rate = user_tax
        new_product.variant_attributes = main_data.get("variant_attributes") or []
        new_product.categories = extracted_categories
        new_product.tags = final_tags
        db.commit()
        db.refresh(new_product)
    else:
        new_product = Product(
            asin=main_data["asin"], parent_asin=main_data.get("parent_asin"), is_variation=False,
            title=main_data.get("title"), brand=main_data.get("brand"), description=main_data.get("description", ""),
            image_url=(main_data.get("images") or [None])[0], images=main_data.get("images") or [],
            rating=main_data.get("rating"), reviews_count=main_data.get("reviews_count"),
            availability=availability_str, is_available=parent_in_stock, stock_quantity=parent_stock,
            amazon_price=main_data.get("price"), price=shopify_payload["price"], 
            markup=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax,
            variant_attributes=main_data.get("variant_attributes") or [], categories=extracted_categories,
            tags=final_tags, shopify_store_id=store.id, shopify_status="active",
        )
        db.add(new_product); db.commit(); db.refresh(new_product)

    print(f"🏪 Creating product on store: {shop_domain}", flush=True)

    # ✅ FIX: Product create karne se pehle FRESH token lein (force_refresh=True)
    print(f"🔄 Refreshing token before product creation for {shop_domain}...", flush=True)
    fresh_token = await _get_valid_access_token(store, db, force_refresh=True)
    print(f"🔑 Fresh token obtained: {fresh_token[:15]}...", flush=True)

    # ✅ NAYA: Compare Price calculate karein
    final_price = shopify_payload["price"]
    compare_price = None
    if compare_price_markup > 0:
        compare_price = final_price * (1 + (compare_price_markup / 100.0))
        print(f"🏷️ Compare Price set: ${compare_price:.2f} (Final: ${final_price:.2f} + {compare_price_markup}%)", flush=True)

    # ✅ shopify_payload mein compareAtPrice add karein
    if compare_price:
        shopify_payload["compare_at_price"] = f"{compare_price:.2f}"

    # ✅ Create product with fresh token
    result = await create_shopify_product(
        shop=shop_domain, 
        access_token=fresh_token,
        product_data=shopify_payload  # ✅ Ab isme compare_at_price bhi hai
    )

    if result and "errors" not in result:
        user_errors = result.get("data", {}).get("productCreate", {}).get("userErrors", [])
        if user_errors:
            print(f"❌ Product Creation User Errors: {user_errors}", flush=True)
            return

        shopify_id = result.get("data", {}).get("productCreate", {}).get("product", {}).get("id")
        if not shopify_id:
            print(f"❌ No product ID returned from Shopify! Result: {result}", flush=True)
            return

        new_product.shopify_product_id = shopify_id
        db.commit()
        print(f"✅ Shopify product created: {shopify_id}", flush=True)

        try:
            token = await _get_valid_access_token(store, db)
            await publish_product(shop_domain, token, shopify_id)
        except Exception as e: 
            print(f"⚠️ Auto-publish failed: {e}", flush=True)
        
        try:
            raw_details = dict(main_data.get("details") or {}); raw_details["asin"] = main_data.get("asin")
            if raw_details:
                await set_product_metafields_smart(shop=shop_domain, access_token=await _get_valid_access_token(store, db), product_id=shopify_id, raw_details=raw_details)
        except Exception as e:
            print(f"⚠️ Metafields set nahi ho paye: {e}", flush=True)
    else:
        print(f"❌ Shopify Error: {result.get('errors')}", flush=True)