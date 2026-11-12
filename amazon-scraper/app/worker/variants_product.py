# app/worker/variants_product.py
from app.models import Product
from app.services.shopify import create_shopify_product_with_variants, publish_product, add_product_to_collections, set_product_metafields_smart
from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token
from app.worker.stock_utils import _get_availability, _resolve_stock

async def process_multi_variant(store, main_data, clean_variants, user_markup, user_markup_type, user_extra, user_tax, final_tags, extracted_categories, shopify_payload, shop_domain, collection_ids, db, default_stock_qty):
    result = await create_shopify_product_with_variants(
        shop=shop_domain, access_token=await _get_valid_access_token(store, db),
        product_data=shopify_payload, variants_raw=clean_variants,
        markup_val=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax,
    )

    if not result or "errors" in result:
        print(f"❌ Shopify GraphQL Error: {result.get('errors')}", flush=True)
        return

    user_errors = result.get("data", {}).get("productCreate", {}).get("userErrors", [])
    if user_errors:
        print(f"❌ Product Creation User Errors: {user_errors}", flush=True)
        return

    shopify_id = result.get("data", {}).get("productCreate", {}).get("product", {}).get("id")
    if not shopify_id:
        print(f"❌ No product ID returned from Shopify!", flush=True)
        return

    print(f"✅ Product created with ID: {shopify_id}", flush=True)

    new_product = db.query(Product).filter(Product.asin == main_data["asin"]).first()
    if new_product:
        new_product.shopify_product_id = shopify_id
        db.commit()

    try:
        saved_variants_count = 0
        for v in clean_variants:
            v_asin = v.get("asin")
            if not v_asin or v_asin == main_data.get("asin"):
                continue

            v_amazon_price = v.get("price") or main_data.get("price") or 0.0
            v_final_price = calculate_final_price(v_amazon_price, user_markup, user_markup_type, user_extra, user_tax)
            v_images = v.get("images") or []
            v_avail_val = v.get("in_stock")
            v_resolved = _resolve_stock(v_avail_val, v.get("stock_qty"), default_stock_qty)
            
            if v_resolved is None:
                v_resolved = 0
                v_in_stock = False
            else:
                v_in_stock = bool(v_avail_val)
                
            v_avail = "In Stock" if v_in_stock else "Out of Stock"
            v_label = v.get("title") or ""
            v_title = f"{main_data.get('title', '')} - {v_label}" if v_label else main_data.get("title", "")

            child_existing = db.query(Product).filter(Product.asin == v_asin).first()
            if child_existing:
                child_existing.shopify_product_id = shopify_id
                child_existing.shopify_store_id = store.id
                child_existing.shopify_status = "active"
                child_existing.price = float(v_final_price)
                child_existing.amazon_price = float(v_amazon_price)
                child_existing.stock_quantity = int(v_resolved)
                child_existing.is_available = v_in_stock
                child_existing.availability = v_avail
            else:
                child_product = Product(
                    asin=v_asin, parent_asin=main_data.get("asin") or main_data.get("parent_asin"), is_variation=True,
                    title=v_title[:255] if v_title else "Untitled Variant", brand=main_data.get("brand"),
                    description=main_data.get("description", ""), image_url=v_images[0] if v_images else None,
                    images=v_images, rating=main_data.get("rating"), reviews_count=main_data.get("reviews_count"),
                    availability=v_avail, is_available=v_in_stock, stock_quantity=int(v_resolved),
                    amazon_price=float(v_amazon_price), price=float(v_final_price),
                    markup=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax,
                    variant_attributes=v.get("option_values") or [], categories=extracted_categories, tags=final_tags,
                    shopify_product_id=shopify_id,
                    shopify_store_id=store.id, shopify_status="active",
                )
                db.add(child_product)
            saved_variants_count += 1

        db.commit()
        print(f"✅ Saved all {saved_variants_count} variants to Database as individual rows!", flush=True)

    except Exception as e:
        print(f"⚠️ Failed to parse variant response: {e}", flush=True)

    try:
        token = await _get_valid_access_token(store, db)
        await publish_product(shop_domain, token, shopify_id)
    except Exception as e: 
        print(f"⚠️ Auto-publish failed: {e}", flush=True)
    
    if collection_ids:
        try:
            token = await _get_valid_access_token(store, db)
            await add_product_to_collections(shop_domain, token, shopify_id, collection_ids)
        except Exception as e: 
            print(f"⚠️ Collection add failed: {e}", flush=True)
    
    try:
        raw_details = dict(main_data.get("details") or {}); raw_details["asin"] = main_data.get("asin")
        if raw_details:
            await set_product_metafields_smart(shop=shop_domain, access_token=await _get_valid_access_token(store, db), product_id=shopify_id, raw_details=raw_details)
    except Exception as e:
        print(f"⚠️ Metafields set nahi ho paye: {e}", flush=True)