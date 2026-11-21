# app/worker/variants_product.py
import re
import traceback
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
    if compare_price_markup > 0:
        final_price = shopify_payload.get("price", 0.0)
        compare_price = final_price * (1 + (compare_price_markup / 100.0))
        print(f"🏷️ Compare Price set: ${compare_price:.2f}", flush=True)
        shopify_payload["compare_at_price"] = f"{compare_price:.2f}"

    clean_variants = reorder_variants_for_default(clean_variants, main_data.get("asin"))
    raw_amazon_title = main_data.get("title") or "Untitled Product"
    shopify_payload["original_title"] = raw_amazon_title

    clean_title = strip_variant_info_from_title(raw_amazon_title, clean_variants, main_data)
    shopify_payload["shopify_title"] = clean_title
    shopify_payload["title"] = clean_title
    
    FILLER_WORDS = {"with", "and", "for", "the", "to", "of", "in", "on", "by", "a", "an", "at", "from"}
    product_title = clean_title or "amazon-product"
    clean_handle_title = re.sub(r"['’]", "", product_title)
    clean_handle_title = re.sub(r"[^a-zA-Z0-9\s]", " ", clean_handle_title)
    all_words = clean_handle_title.split()
    meaningful_words = [w.lower() for w in all_words if w.lower() not in FILLER_WORDS]
    selected_words = (meaningful_words or [w.lower() for w in all_words])[:5]
    base_handle = "-".join(selected_words) if selected_words else "product"

    existing_products = db.query(Product).filter(Product.shopify_handle.like(f"{base_handle}%")).all()
    final_handle = f"{base_handle}-{len(existing_products) + 1}" if existing_products else base_handle
    shopify_payload["handle"] = final_handle

    # ==========================================
    # 🔥 STEP 1: SHOPIFY API CALL (Agar fail ho toh DB save hoga, par code nahi rukega)
    # ==========================================
    shopify_id = None
    token = await _get_valid_access_token(store, db)
    
    print(f"🚀 [Shopify] Attempting to create product on Shopify...", flush=True)
    try:
        result = await create_shopify_product_with_variants(
            shop=shop_domain, access_token=token,
            product_data=shopify_payload, variants_raw=clean_variants,
            markup_val=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax
        )
        if result and "data" in result:
            shopify_id = result.get("data", {}).get("productCreate", {}).get("product", {}).get("id")
            print(f"✅ [Shopify] Product created with ID: {shopify_id}", flush=True)
        else:
            print(f"⚠️ [Shopify] Product creation failed or returned no ID. Proceeding with DB save only.", flush=True)
    except Exception as e:
        print(f"❌ [Shopify] API crashed: {e}", flush=True)
        traceback.print_exc()

    # ==========================================
    # 🔥 STEP 2: PARENT PRODUCT SAVE (DB) - Chahe Shopify fail ho ya pass
    # ==========================================
    try:
        parent_asin_upper = main_data["asin"].upper()
        new_product = db.query(Product).filter(Product.asin == parent_asin_upper).first()
        
        parent_available = _get_availability(main_data)
        parent_stock_qty = _resolve_stock(parent_available, main_data.get("stock_qty"), default_stock_qty)
        parent_in_stock = bool(parent_available) if parent_stock_qty is not None else False
        parent_stock = parent_stock_qty or 0
        availability_str = "In Stock" if parent_in_stock else "Out of Stock"

        if not new_product:
            new_product = Product(
                asin=parent_asin_upper, parent_asin=main_data.get("parent_asin"), is_variation=False,
                title=main_data.get("title"), brand=main_data.get("brand"), description=main_data.get("description", ""),
                image_url=(main_data.get("images") or [None])[0], images=main_data.get("images") or [],
                rating=main_data.get("rating"), reviews_count=main_data.get("reviews_count"),
                availability=availability_str, is_available=parent_in_stock, stock_quantity=parent_stock,
                amazon_price=main_data.get("price"), price=shopify_payload["price"],
                markup=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax,
                variant_attributes=main_data.get("variant_attributes") or [], categories=extracted_categories,
                tags=final_tags, shopify_store_id=store.id, shopify_status="pending" if not shopify_id else "active",
                shopify_product_id=shopify_id, shopify_handle=final_handle,
            )
            db.add(new_product)
        else:
            new_product.shopify_product_id = shopify_id
            new_product.shopify_store_id = store.id
            new_product.shopify_status = "pending" if not shopify_id else "active"
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
        
        db.commit()
        db.refresh(new_product)
        print(f"✅ [DB SUCCESS] Parent saved in DB! ID: {new_product.id}", flush=True)
    except Exception as e:
        db.rollback()
        print(f"❌ [DB ERROR] Parent Save Failed: {e}", flush=True)
        traceback.print_exc()
        return

    # ==========================================
    # 🔥 STEP 3: CHILD PRODUCTS SAVE (DB)
    # ==========================================
    saved_variants_count = 0
    for v in clean_variants:
        try:
            v_asin_upper = v.get("asin", "").upper()
            if not v_asin_upper or v_asin_upper == parent_asin_upper:
                continue

            v_amazon_price = v.get("price") or main_data.get("price") or 0.0
            v_final_price = calculate_final_price(v_amazon_price, user_markup, user_markup_type, user_extra, user_tax)
            v_images = v.get("images") or []
            v_resolved = _resolve_stock(v.get("in_stock"), v.get("stock_qty"), default_stock_qty) or 0
            v_in_stock = v_resolved > 0
            v_avail = "In Stock" if v_in_stock else "Out of Stock"
            v_title = f"{main_data.get('title', '')} - {v.get('title', '')}" if v.get('title') else main_data.get("title", "")

            child_existing = db.query(Product).filter(Product.asin == v_asin_upper).first()
            if not child_existing:
                child_product = Product(
                    asin=v_asin_upper, parent_asin=parent_asin_upper, is_variation=True,
                    title=v_title[:255], brand=main_data.get("brand"), description=main_data.get("description", ""),
                    image_url=v_images[0] if v_images else None, images=v_images,
                    rating=main_data.get("rating"), reviews_count=main_data.get("reviews_count"),
                    availability=v_avail, is_available=v_in_stock, stock_quantity=int(v_resolved),
                    amazon_price=float(v_amazon_price), price=float(v_final_price),
                    markup=user_markup, markup_type=user_markup_type, extra_percent=user_extra, tax_rate=user_tax,
                    variant_attributes=v.get("option_values") or [], categories=extracted_categories, tags=final_tags,
                    shopify_product_id=shopify_id, shopify_store_id=store.id, 
                    shopify_status="pending" if not shopify_id else "active", shopify_handle=final_handle,
                )
                db.add(child_product)
            
            db.commit()
            saved_variants_count += 1
        except Exception as e:
            db.rollback()
            print(f"⚠️ Variant {v.get('asin')} DB save failed: {e}", flush=True)

    try:
        store.product_count = (store.product_count or 0) + saved_variants_count + 1
        db.commit()
        print(f"✅ [DB SUCCESS] Saved {saved_variants_count} variants in DB! Count updated.", flush=True)
    except Exception as e:
        db.rollback()
        print(f"⚠️ Count update failed: {e}", flush=True)

    # ==========================================
    # 🔥 STEP 4: POST-SHOPIFY TASKS (Sirf agar product bana hai)
    # ==========================================
    if shopify_id:
        try:
            await publish_product(shop_domain, token, shopify_id)
            print(f"✅ Product Published", flush=True)
        except Exception as e:
            print(f"⚠️ Publish failed: {e}", flush=True)

        if collection_ids:
            try:
                await add_product_to_collections(shop_domain, token, shopify_id, collection_ids)
                print(f"✅ Added to collections", flush=True)
            except Exception as e:
                print(f"⚠️ Collection add failed: {e}", flush=True)
        
        try:
            raw_details = dict(main_data.get("details") or {})
            raw_details["asin"] = main_data.get("asin")
            if shopify_payload.get("size_chart"):
                raw_details["size_chart"] = shopify_payload["size_chart"]
            if raw_details:
                await set_product_metafields_smart(shop=shop_domain, access_token=token, product_id=shopify_id, raw_details=raw_details)
        except Exception as e:
            print(f"⚠️ Metafields failed: {e}", flush=True)