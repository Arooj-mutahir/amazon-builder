# app/worker/variants_product.py
import re
from app.models import Product
from app.services.shopify import create_shopify_product_with_variants, publish_product, add_product_to_collections, set_product_metafields_smart
from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token
from app.worker.stock_utils import _get_availability, _resolve_stock
from app.services.shopify.client import shopify_graphql
from app.worker.title_cleaner import strip_variant_info_from_title, reorder_variants_for_default
from app.database import SessionLocal

async def process_multi_variant(
    store, main_data, clean_variants, user_markup, user_markup_type, 
    user_extra, user_tax, final_tags, extracted_categories, shopify_payload, 
    shop_domain, collection_ids, db, default_stock_qty,
    compare_price_markup: float = 0.0
):
    
    # ✅ Compare Price
    compare_price = None
    if compare_price_markup > 0:
        final_price = shopify_payload.get("price", 0.0)
        compare_price = final_price * (1 + (compare_price_markup / 100.0))
        print(f"🏷️ Compare Price set: ${compare_price:.2f}", flush=True)
        shopify_payload["compare_at_price"] = f"{compare_price:.2f}"

    # ==========================================
    # ✅ 1. Variant Reordering
    # ==========================================
    clean_variants = reorder_variants_for_default(clean_variants, main_data.get("asin"))

    # ==========================================
    # ✅ 2. Title & Handle Logic
    # ==========================================
    raw_amazon_title = main_data.get("title") or "Untitled Product"
    shopify_payload["original_title"] = raw_amazon_title

    clean_title = strip_variant_info_from_title(raw_amazon_title, clean_variants, main_data)
    shopify_payload["shopify_title"] = clean_title
    shopify_payload["title"] = clean_title
    print(f"🏷️ Final Shopify Title: {clean_title}", flush=True)

    FILLER_WORDS = {"with", "and", "for", "the", "to", "of", "in", "on", "by", "a", "an", "at", "from"}
    product_title = clean_title or "amazon-product"
    clean_handle_title = re.sub(r"['’]", "", product_title)
    clean_handle_title = re.sub(r"[^a-zA-Z0-9\s]", " ", clean_handle_title)
    all_words = clean_handle_title.split()
    meaningful_words = [w.lower() for w in all_words if w.lower() not in FILLER_WORDS]
    selected_words = (meaningful_words or [w.lower() for w in all_words])[:5]
    base_handle = "-".join(selected_words) if selected_words else "product"

    # Duplicate Handle Check (Fast DB Query)
    existing_products = db.query(Product).filter(Product.shopify_handle.like(f"{base_handle}%")).all()
    if existing_products:
        suffix = len(existing_products) + 1
        final_handle = f"{base_handle}-{suffix}"
    else:
        final_handle = base_handle

    shopify_payload["handle"] = final_handle
    print(f"🔗 Final Clean Handle: {final_handle}", flush=True)

    # ==========================================
    # ✅ 3. SHOPIFY API CALL (Long Process)
    # ==========================================
    token = await _get_valid_access_token(store, db)
    result = await create_shopify_product_with_variants(
        shop=shop_domain, access_token=token,
        product_data=shopify_payload, variants_raw=clean_variants,
        markup_val=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax
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

    # ==========================================
    # ✅ 4. Update Default Variant Title (API Call)
    # ==========================================
    try:
        get_variants_query = """
        query getProductVariants($id: ID!) {
          product(id: $id) {
            variants(first: 1) { nodes { id } }
          }
        }
        """
        variant_res = await shopify_graphql(shop_domain, token, get_variants_query, {"id": shopify_id})
        default_variant_nodes = (variant_res.get("data", {}).get("product", {}).get("variants", {}).get("nodes") or [])
        
        if default_variant_nodes:
            default_variant_id = default_variant_nodes[0]["id"]
            update_mutation = """
            mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
              productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants { id title }
                userErrors { field message }
              }
            }
            """
            update_res = await shopify_graphql(shop_domain, token, update_mutation, {
                "productId": shopify_id,
                "variants": [{"id": default_variant_id, "title": main_data.get("title", "")[:255]}]
            })
            errs = (update_res.get("data", {}).get("productVariantsBulkUpdate") or {}).get("userErrors") or []
            if errs:
                print(f"⚠️ Default variant title update failed: {errs}", flush=True)
            else:
                print(f"✅ Default variant title updated.", flush=True)
    except Exception as e:
        print(f"⚠️ Default variant title update error: {e}", flush=True)

    # ==========================================
    # ✅ 5. PARENT PRODUCT SAVE (DB)
    # ==========================================
    new_product = db.query(Product).filter(Product.asin == main_data["asin"]).first()
    
    parent_available = _get_availability(main_data)
    parent_stock_raw = main_data.get("stock_qty")
    parent_stock_qty = _resolve_stock(parent_available, parent_stock_raw, default_stock_qty)
    parent_in_stock = bool(parent_available) if parent_stock_qty is not None else False
    parent_stock = parent_stock_qty or 0
    availability_str = "In Stock" if parent_in_stock else "Out of Stock"

    if not new_product:
        new_product = Product(
            asin=main_data["asin"], 
            parent_asin=main_data.get("parent_asin"), 
            is_variation=False,
            title=main_data.get("title"), 
            brand=main_data.get("brand"), 
            description=main_data.get("description", ""),
            image_url=(main_data.get("images") or [None])[0], 
            images=main_data.get("images") or [],
            rating=main_data.get("rating"), 
            reviews_count=main_data.get("reviews_count"),
            availability=availability_str, 
            is_available=parent_in_stock, 
            stock_quantity=parent_stock,
            amazon_price=main_data.get("price"), 
            price=shopify_payload["price"], 
            markup=user_markup, 
            markup_type=user_markup_type, 
            extra_percent=user_extra, 
            tax_rate=user_tax,
            variant_attributes=main_data.get("variant_attributes") or [], 
            categories=extracted_categories,
            tags=final_tags, 
            shopify_store_id=store.id, 
            shopify_status="active",
            shopify_product_id=shopify_id,
            shopify_handle=final_handle,
        )
        db.add(new_product)
        print(f"✅ Parent product created in DB", flush=True)
    else:
        new_product.shopify_product_id = shopify_id
        new_product.shopify_store_id = store.id
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
        new_product.categories = extracted_categories
        new_product.tags = final_tags
        new_product.shopify_handle = final_handle
        print(f"✅ Parent product updated in DB", flush=True)
        
    db.commit()

    # ==========================================
    # ✅ 6. CHILD PRODUCTS SAVE (DB)
    # ==========================================
    try:
        # 🔥 FIX: Default variant bhi count karo
        saved_variants_count = len(clean_variants)  # Total variants (including default)

        for v in clean_variants:
            v_asin = v.get("asin")
            if not v_asin or v_asin == main_data.get("asin"):
                continue  # Default variant already counted

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
                child_existing.markup = user_markup
                child_existing.markup_type = user_markup_type
                child_existing.extra_percent = user_extra
                child_existing.tax_rate = user_tax
                child_existing.shopify_handle = final_handle
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
                    shopify_handle=final_handle,
                )
                db.add(child_product)

        # 🔥 FIX: PRODUCT COUNT UPDATE (Default variant bhi count hoga)
        store.product_count = (store.product_count or 0) + saved_variants_count
        print(f"📈 Product count updated: {store.product_count} (+{saved_variants_count})", flush=True)

        db.commit()
        print(f"✅ Saved all {saved_variants_count} variants to Database!", flush=True)

    except Exception as e:
        print(f"⚠️ Failed to parse variant response: {e}", flush=True)
        db.rollback()

    # ==========================================
    # ✅ 7. Publish, Collections, Metafields
    # 🔥 FIX: Yahan NAYA SESSION use karo
    # ==========================================
    new_db = SessionLocal()
    try:
        await publish_product(shop_domain, token, shopify_id)
        print(f"✅ Product Published Successfully", flush=True)
        
        if collection_ids:
            try:
                print(f"🛒 Adding product to collections: {collection_ids}", flush=True)
                await add_product_to_collections(shop_domain, token, shopify_id, collection_ids)
                print(f"✅ Product added to collections successfully!", flush=True)
            except Exception as e: 
                print(f"❌ Collection add failed: {e}", flush=True)
        else:
            print(f"⚠️ No collection_ids received (empty list). Product not added to any collection.", flush=True)
        
        try:
            raw_details = dict(main_data.get("details") or {})
            raw_details["asin"] = main_data.get("asin")
            if shopify_payload.get("size_chart"):
                raw_details["size_chart"] = shopify_payload["size_chart"]
                print(f"📏 Size chart added to metafields", flush=True)
                
            if raw_details:
                await set_product_metafields_smart(shop=shop_domain, access_token=token, product_id=shopify_id, raw_details=raw_details)
        except Exception as e:
            print(f"⚠️ Metafields set nahi ho paye: {e}", flush=True)
    finally:
        new_db.close()