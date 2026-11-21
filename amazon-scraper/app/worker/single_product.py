# app/worker/single_product.py
import traceback
import re
from app.database import SessionLocal
from app.models import Product, ShopifyStore
from app.services.shopify import create_shopify_product, publish_product, add_product_to_collections, set_product_metafields_smart
from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token
from app.worker.stock_utils import _get_availability, _resolve_stock
from app.worker.title_cleaner import strip_variant_info_from_title

async def process_single_variant(
    store, main_data, user_markup, user_markup_type, user_extra, user_tax, 
    final_tags, extracted_categories, shopify_payload, shop_domain, db, default_stock_qty,
    compare_price_markup: float = 0.0,
    collection_ids: list = None
):
    new_product = None
    existing = db.query(Product).filter(Product.asin == main_data["asin"]).first()
    
    parent_available = _get_availability(main_data)
    parent_stock_raw = main_data.get("stock_qty")
    parent_stock_qty = _resolve_stock(parent_available, parent_stock_raw, default_stock_qty)
    parent_in_stock = bool(parent_available) if parent_stock_qty is not None else False
    parent_stock = parent_stock_qty or 0
    availability_str = "In Stock" if parent_in_stock else "Out of Stock"

    # ==========================================
    # ✅ 1. Handle Generation
    # ==========================================
    raw_amazon_title = main_data.get("title") or "Untitled Product"
    shopify_payload["original_title"] = raw_amazon_title

    clean_title = strip_variant_info_from_title(raw_amazon_title, [], main_data)
    shopify_payload["shopify_title"] = clean_title
    shopify_payload["title"] = clean_title
    print(f"🏷️ Final Shopify Title (Original without variant): {clean_title}", flush=True)

    FILLER_WORDS = {"with", "and", "for", "the", "to", "of", "in", "on", "by", "a", "an", "at", "from"}
    product_title = clean_title or "amazon-product"
    clean_handle_title = re.sub(r"['’]", "", product_title)              
    clean_handle_title = re.sub(r"[^a-zA-Z0-9\s]", " ", clean_handle_title)     
    all_words = clean_handle_title.split()
    meaningful_words = [w.lower() for w in all_words if w.lower() not in FILLER_WORDS]
    selected_words = (meaningful_words or [w.lower() for w in all_words])[:5]
    base_handle = "-".join(selected_words) if selected_words else "product"

    # Duplicate Handle Check
    existing_products = db.query(Product).filter(Product.shopify_handle.like(f"{base_handle}%")).all()
    if existing_products:
        suffix = len(existing_products) + 1
        final_handle = f"{base_handle}-{suffix}"
    else:
        final_handle = base_handle

    shopify_payload["handle"] = final_handle
    print(f"🔗 Final Clean Handle: {final_handle}", flush=True)

    # ==========================================
    # ✅ 2. DB Save/Update (BEFORE Shopify API)
    # ==========================================
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
        new_product.shopify_handle = final_handle 
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
            shopify_handle=final_handle, 
        )
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

    # ==========================================
    # ✅ 3. Shopify API Call
    # ==========================================
    print(f"🏪 Creating product on store: {shop_domain}", flush=True)

    print(f"🔄 Refreshing token before product creation for {shop_domain}...", flush=True)
    fresh_token = await _get_valid_access_token(store, db, force_refresh=True)
    print(f"🔑 Fresh token obtained: {fresh_token[:15]}...", flush=True)

    final_price = shopify_payload["price"]
    compare_price = None
    if compare_price_markup > 0:
        compare_price = final_price * (1 + (compare_price_markup / 100.0))
        print(f"🏷️ Compare Price set: ${compare_price:.2f}", flush=True)
    if compare_price:
        shopify_payload["compare_at_price"] = f"{compare_price:.2f}"

    # ✅ Create product
    result = await create_shopify_product(
        shop=shop_domain, 
        access_token=fresh_token,
        product_data=shopify_payload
    )

    if result and "errors" not in result:
        user_errors = result.get("data", {}).get("productCreate", {}).get("userErrors", [])
        if user_errors:
            print(f"❌ Product Creation User Errors: {user_errors}", flush=True)
            return

        shopify_id = result.get("data", {}).get("productCreate", {}).get("product", {}).get("id")
        if not shopify_id:
            print(f"❌ No product ID returned from Shopify!", flush=True)
            return

        # ==========================================
        # ✅ 4. Shopify ID ko DB mein Update karo + PRODUCT COUNT
        # ==========================================
        new_product.shopify_product_id = shopify_id
        
        # 🔥 FIX: SINGLE PRODUCT KA COUNT UPDATE KARO
        store.product_count = (store.product_count or 0) + 1
        print(f"📈 Product count updated: {store.product_count} (+1)", flush=True)
        
        db.commit()
        print(f"✅ Shopify product created: {shopify_id}", flush=True)

        # 🔥 FIX: db.close() HATA DIYA HAI (worker.py khud close karega)

        try:
            await publish_product(shop_domain, fresh_token, shopify_id)
        except Exception as e: 
            print(f"⚠️ Auto-publish failed: {e}", flush=True)
        
        # ==========================================
        # ✅ 5. Add to Collections
        # ==========================================
        if collection_ids:
            try:
                print(f"🛒 Adding product to collections: {collection_ids}", flush=True)
                await add_product_to_collections(shop_domain, fresh_token, shopify_id, collection_ids)
                print(f"✅ Product added to collections successfully!", flush=True)
            except Exception as e: 
                print(f"❌ Collection add failed: {e}", flush=True)

        try:
            raw_details = dict(main_data.get("details") or {})
            raw_details["asin"] = main_data.get("asin")
            if shopify_payload.get("size_chart"):
                raw_details["size_chart"] = shopify_payload["size_chart"]
                print(f"📏 Size chart added to metafields", flush=True)
                
            if raw_details:
                await set_product_metafields_smart(shop=shop_domain, access_token=fresh_token, product_id=shopify_id, raw_details=raw_details)
        except Exception as e:
            print(f"⚠️ Metafields set nahi ho paye: {e}", flush=True)
    else:
        print(f"❌ Shopify Error: {result.get('errors')}", flush=True)