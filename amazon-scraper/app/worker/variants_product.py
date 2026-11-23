# app/worker/variants_product.py
import re
import traceback
from app.models import Product, ShopifyStore
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
    
    # ✅ 1. Compare Price Logic
    if compare_price_markup > 0:
        final_price = shopify_payload.get("price", 0.0)
        compare_price = final_price * (1 + (compare_price_markup / 100.0))
        print(f"🏷️ Compare Price set: ${compare_price:.2f}", flush=True)
        shopify_payload["compare_at_price"] = f"{compare_price:.2f}"

    # ✅ 2. Title & Handle Logic
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
    # 🔥 3. DB SAVE
    # ==========================================
    db_save = SessionLocal()
    parent_asin_upper = main_data["asin"].upper()
    saved_variants_count = 0

    try:
        # --- Parent Product Save ---
        new_product = db_save.query(Product).filter(Product.asin == parent_asin_upper).first()
        
        # 🔥 YEH HAI ASLI FIX: Seedha main_data se uthao
        parent_in_stock = bool(main_data.get("is_available", False))
        parent_stock = int(main_data.get("stock_qty", 0)) if parent_in_stock else 0
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
                tags=final_tags, shopify_store_id=store.id, shopify_status="pending",
                shopify_handle=final_handle,
            )
            db_save.add(new_product)
            print(f"✅ [DB] Parent product saved in DB!", flush=True)
        else:
            new_product.shopify_store_id = store.id
            new_product.shopify_status = "pending"
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
            print(f"✅ [DB] Parent product updated in DB!", flush=True)
        
        db_save.commit()
        db_save.refresh(new_product)
        saved_variants_count += 1

        # --- Child Products Save (Loop) ---
        for v in clean_variants:
            try:
                v_asin_upper = v.get("asin", "").upper()
                if not v_asin_upper or v_asin_upper == parent_asin_upper:
                    continue

                v_amazon_price = v.get("price") or main_data.get("price") or 0.0
                v_final_price = calculate_final_price(v_amazon_price, user_markup, user_markup_type, user_extra, user_tax)
                v_images = v.get("images") or []

                # 🔥 FIX: Child ke liye bhi main_data use karo
                v_in_stock = bool(v.get("in_stock", parent_in_stock))
                v_resolved = int(v.get("stock_qty", parent_stock)) if v_in_stock else 0

                v_avail = "In Stock" if v_in_stock else "Out of Stock"
                v_title = f"{main_data.get('title', '')} - {v.get('title', '')}" if v.get('title') else main_data.get("title", "")

                child_existing = db_save.query(Product).filter(Product.asin == v_asin_upper).first()
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
                        shopify_store_id=store.id, shopify_status="pending", shopify_handle=final_handle,
                    )
                    db_save.add(child_product)
                else:
                    child_existing.shopify_store_id = store.id
                    child_existing.shopify_status = "pending"
                    child_existing.price = float(v_final_price)
                    child_existing.amazon_price = float(v_amazon_price)
                    child_existing.stock_quantity = int(v_resolved)
                    child_existing.is_available = v_in_stock
                    child_existing.availability = v_avail
                
                db_save.commit()
                saved_variants_count += 1

            except Exception as e:
                db_save.rollback()
                print(f"⚠️ Variant {v.get('asin')} DB save failed: {e}", flush=True)

        # Store count update
        store_db = db_save.query(ShopifyStore).filter(ShopifyStore.id == store.id).first()
        if store_db:
            store_db.product_count = (store_db.product_count or 0) + saved_variants_count
            db_save.commit()
            print(f"📈 [DB] Product count updated: {store_db.product_count} (+{saved_variants_count})", flush=True)

    except Exception as e:
        db_save.rollback()
        print(f"❌ [DB ERROR] Save Failed: {e}", flush=True)
        traceback.print_exc()
        return
    finally:
        db_save.close()

    # ==========================================
    # 🔥 4. SHOPIFY API CALL
    # ==========================================
    print(f"🚀 [Shopify] Creating product with {len(clean_variants)} variants...", flush=True)
    
    token_db = SessionLocal()
    try:
        store_token = token_db.query(ShopifyStore).filter(ShopifyStore.id == store.id).first()
        token = await _get_valid_access_token(store_token, token_db, force_refresh=True)
    finally:
        token_db.close()

    shopify_id = None
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
            print(f"⚠️ [Shopify] Product creation failed. Error: {result}", flush=True)
    except Exception as e:
        print(f"❌ [Shopify] API crashed: {e}", flush=True)
        traceback.print_exc()

    # ==========================================
    # 🔥 5. UPDATE DB WITH SHOPIFY IDS
    # ==========================================
    if shopify_id:
        update_db = SessionLocal()
        try:
            parent_db = update_db.query(Product).filter(Product.asin == parent_asin_upper).first()
            if parent_db:
                parent_db.shopify_product_id = shopify_id
                parent_db.shopify_status = "active"
            
            for v in clean_variants:
                v_asin = v.get("asin", "").upper()
                if v_asin and v_asin != parent_asin_upper:
                    child_db = update_db.query(Product).filter(Product.asin == v_asin).first()
                    if child_db:
                        child_db.shopify_product_id = shopify_id
                        child_db.shopify_status = "active"
            
            update_db.commit()
            print(f"✅ [DB] Shopify IDs updated in DB. Status = active", flush=True)
        except Exception as e:
            update_db.rollback()
            print(f"⚠️ [DB] Failed to update Shopify IDs: {e}", flush=True)
        finally:
            update_db.close()

        # Publish & Collections
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
    else:
        print(f"⚠️ Product was not created on Shopify. DB records are in 'pending' state.", flush=True)