# app/worker/sync_job.py
import traceback
import asyncio
from datetime import datetime
from app.database import SessionLocal
from app.models import Product, ShopifyStore
from app.services.amazon_bridge import get_shopify_product_data
from app.services.shopify import shopify_graphql, _set_inventory_quantities
from app.worker.stock_utils import _get_availability, _resolve_stock

_location_cache = {}


async def _get_primary_location_cached(store, db):
    key = (store.shop_domain, store.id)
    if key in _location_cache:
        return _location_cache[key]

    from app.services.shopify.locations import get_primary_location
    from app.api.routes.shopify.helpers import _get_valid_access_token

    token = await _get_valid_access_token(store, db)
    loc = await get_primary_location(store.shop_domain, token)
    _location_cache[key] = loc
    return loc


async def _get_product_actual_location(store, token, inventory_item_id, fallback_location):
    query = """
    query getItemLocations($id: ID!) {
      inventoryItem(id: $id) {
        inventoryLevels(first: 1) {
          nodes { location { id name } }
        }
      }
    }
    """
    try:
        res = await shopify_graphql(store.shop_domain, token, query, {"id": inventory_item_id})
        levels = res.get("data", {}).get("inventoryItem", {}).get("inventoryLevels", {}).get("nodes", [])
        if levels and len(levels) > 0:
            return levels[0]["location"]["id"]
    except Exception as e:
        print(f"   ⚠️ Could not fetch actual location: {e}", flush=True)

    return fallback_location


def _is_store_sync_eligible(store, db) -> bool:
    """Check if store is eligible for sync."""
    if not store:
        return False

    if store.trial_ends_at and store.trial_ends_at < datetime.utcnow():
        if not store.plan_expires_at and (store.plan_status or "").lower() == "active":
            print(f"⏰ Trial expired for {store.shop_domain} → downgrading", flush=True)
            store.plan = "basic"
            store.plan_status = "expired"
            store.auto_sync_enabled = False
            try:
                db.commit()
            except Exception:
                db.rollback()
            return False

    if (store.plan or "").lower() != "advance":
        return False

    plan_status = getattr(store, "plan_status", None)
    if plan_status and plan_status.lower() != "active":
        return False

    if not bool(getattr(store, "auto_sync_enabled", False)):
        return False

    expires_at = getattr(store, "plan_expires_at", None)
    if expires_at and expires_at < datetime.utcnow():
        print(f"   ⏰ Plan expired for {store.shop_domain} → downgrading", flush=True)
        store.plan = "basic"
        if hasattr(store, "plan_status"):
            store.plan_status = "expired"
        store.auto_sync_enabled = False
        try:
            db.commit()
        except Exception:
            db.rollback()
        return False

    return True


async def sync_prices_job(store_id: int = None):
    print(f"\n⏰ [CRON JOB] Starting Price + Stock Sync for {'Store ID: ' + str(store_id) if store_id else 'ALL Stores'}...", flush=True)

    from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token

    db = SessionLocal()
    try:
        query = db.query(Product).filter(
            Product.shopify_product_id.isnot(None)
        )

        if store_id:
            query = query.filter(Product.shopify_store_id == store_id)
            print(f"🎯 Filtering products for Store ID: {store_id}", flush=True)

        products = query.all()
        print(f"🔍 Found {len(products)} products with Shopify IDs to check.\n", flush=True)

        _eligible_cache = {}

        for product in products:
            try:
                store = db.query(ShopifyStore).filter(ShopifyStore.id == product.shopify_store_id).first()
                if not store:
                    continue

                if store.id not in _eligible_cache:
                    _eligible_cache[store.id] = _is_store_sync_eligible(store, db)

                if not _eligible_cache[store.id]:
                    print(f"⏭️  Skipping {product.asin} — store not eligible", flush=True)
                    continue

                print(f"=======================================================", flush=True)
                print(f"🔎 Checking ASIN: {product.asin} (Shopify ID: {product.shopify_product_id})", flush=True)

                store_markup = float(store.default_markup if store.default_markup is not None else 0.0)
                store_markup_type = str(store.default_markup_type or "fixed").lower()
                store_extra = float(store.default_extra_percent if store.default_extra_percent is not None else 0.0)
                store_tax = float(store.default_tax_rate if store.default_tax_rate is not None else 0.0)
                default_stock = int(getattr(store, "default_stock_qty", 0) or 0)
                store_compare_markup = float(getattr(store, "default_compare_price_markup", 0.0) or 0.0)

                markup_display = f"${store_markup:.2f}" if store_markup_type == "fixed" else f"{store_markup}%"
                print(f"   ⚙️  UI Settings: Type={store_markup_type.upper()} | Markup={markup_display} | Extra={store_extra}% | Tax={store_tax}% | Compare={store_compare_markup}%", flush=True)

                child_products = []
                if not product.is_variation:
                    child_products = db.query(Product).filter(
                        Product.parent_asin == product.asin,
                        Product.is_variation == True
                    ).all()

                all_products = [product] + child_products
                print(f"   📦 Total variants to sync: {len(all_products)}", flush=True)

                asin_to_scrape = product.parent_asin if product.is_variation and product.parent_asin else product.asin

                scrape_timeout = max(60.0, float(len(child_products) * 3.5 + 30.0))
                try:
                    latest_data = await asyncio.wait_for(
                        get_shopify_product_data(asin_to_scrape, default_stock_qty=default_stock, fetch_all_variants=True),
                        timeout=scrape_timeout
                    )
                except asyncio.TimeoutError:
                    print(f"   ⏳ Timeout fetching Amazon data", flush=True)
                    continue
                except Exception as e:
                    print(f"   ⚠️ Scrape failed: {e}", flush=True)
                    continue

                latest_amazon_price = float(latest_data.get("price") or 0.0)

                if latest_amazon_price <= 0:
                    print(f"   ⚠️ Amazon Price is $0.00", flush=True)

                latest_parent_stock = latest_data.get("stock_qty")
                latest_parent_available = _get_availability(latest_data)
                resolved_parent_stock = _resolve_stock(latest_parent_available, latest_parent_stock, default_stock)

                variants_by_asin = {v["asin"]: v for v in (latest_data.get("variant_products") or []) if v.get("asin")}

                print(f"   💰 Calculating prices & updating Database...", flush=True)
                for prod in all_products:
                    if prod.asin == product.asin:
                        v_amazon_price = latest_amazon_price if latest_amazon_price > 0 else prod.amazon_price
                        v_available = latest_parent_available
                        v_stock = resolved_parent_stock
                    else:
                        v_data = variants_by_asin.get(prod.asin) or {}
                        fetched_p = v_data.get("price")
                        v_amazon_price = float(fetched_p) if (fetched_p and float(fetched_p) > 0) else latest_amazon_price

                        if v_amazon_price <= 0:
                            v_amazon_price = prod.amazon_price

                        v_available = _get_availability(v_data) if (v_data.get("in_stock") is not None or v_data.get("is_available") is not None) else latest_parent_available
                        v_raw_stock = v_data.get("stock_qty") if v_data.get("stock_qty") is not None else latest_parent_stock
                        v_stock = _resolve_stock(v_available, v_raw_stock, default_stock)

                    if v_amazon_price and v_amazon_price > 0:
                        v_final_price = calculate_final_price(v_amazon_price, store_markup, store_markup_type, store_extra, store_tax)
                        prod.price = float(v_final_price)
                        prod.amazon_price = float(v_amazon_price)

                    prod.markup = store_markup
                    prod.markup_type = store_markup_type
                    prod.extra_percent = store_extra
                    prod.tax_rate = store_tax

                    if v_stock is not None:
                        prod.stock_quantity = int(v_stock)
                        prod.is_available = bool(v_available) if v_available is not None else False
                        prod.availability = "In Stock" if prod.is_available else "Out of Stock"

                    v_type_label = "Parent" if not prod.is_variation else "Child"
                    print(f"      👉 ASIN {prod.asin} ({v_type_label}): Amazon=${v_amazon_price or 0.0:.2f} -> UI Final=${prod.price or 0.0:.2f} | Stock={prod.stock_quantity} ({prod.availability})", flush=True)

                # 🔥 HAR PRODUCT KE BAAD COMMIT KARO (Safer)
                try:
                    db.commit()
                    print(f"   💾 Database updated successfully.", flush=True)
                except Exception as commit_err:
                    db.rollback()
                    print(f"   ⚠️ DB Commit Failed (will retry): {commit_err}", flush=True)
                    continue  # Agle product pe jao

                # Shopify Update
                token = await _get_valid_access_token(store, db)
                shopify_product_id = product.shopify_product_id
                if shopify_product_id and not str(shopify_product_id).startswith("gid://shopify/"):
                    shopify_product_id = f"gid://shopify/Product/{shopify_product_id}"

                fresh_variant_map = {}
                fresh_inventory_map = {}

                if shopify_product_id:
                    inv_query = """
                    query getProductInventory($id: ID!) {
                      product(id: $id) {
                        id title variants(first: 100) { nodes { id sku price inventoryItem { id } } }
                      }
                    }
                    """
                    inv_result = await shopify_graphql(store.shop_domain, token, inv_query, {"id": shopify_product_id})
                    product_node = inv_result.get("data", {}).get("product")

                    if not product_node:
                        print(f"   ⚠️ Product not found by ID. Searching by SKU...", flush=True)
                        search_query = """
                        query findProductBySku($query: String!) {
                          products(first: 1, query: $query) {
                            nodes { id title variants(first: 100) { nodes { id sku price inventoryItem { id } } } }
                          }
                        }
                        """
                        search_res = await shopify_graphql(store.shop_domain, token, search_query, {"query": f"sku:{product.asin}"})
                        nodes_found = search_res.get("data", {}).get("products", {}).get("nodes", [])
                        if nodes_found:
                            product_node = nodes_found[0]
                            shopify_product_id = product_node["id"]
                            product.shopify_product_id = shopify_product_id
                            try:
                                db.commit()
                            except Exception:
                                db.rollback()

                    if product_node:
                        for node in product_node.get("variants", {}).get("nodes", []):
                            sku = node.get("sku")
                            if sku:
                                fresh_variant_map[sku] = node["id"]
                                if node.get("inventoryItem", {}).get("id"):
                                    fresh_inventory_map[sku] = node["inventoryItem"]["id"]

                price_updates = []
                stock_updates = []
                updated_inv_ids = set()

                default_location_id = getattr(store, "shopify_location_id", None) or await _get_primary_location_cached(store, db)

                for prod in all_products:
                    fresh_v_id = fresh_variant_map.get(prod.asin)
                    if fresh_v_id and prod.price:
                        update_payload = {
                            "id": fresh_v_id,
                            "price": f"{prod.price:.2f}"
                        }

                        if store_compare_markup > 0:
                            compare_price = prod.price * (1 + (store_compare_markup / 100.0))
                            update_payload["compareAtPrice"] = f"{compare_price:.2f}"
                        else:
                            update_payload["compareAtPrice"] = None

                        price_updates.append(update_payload)

                    inv_id = fresh_inventory_map.get(prod.asin)
                    if inv_id and inv_id not in updated_inv_ids:
                        actual_loc_id = await _get_product_actual_location(store, token, inv_id, default_location_id)

                        if actual_loc_id:
                            stock_updates.append({
                                "inventoryItemId": inv_id,
                                "locationId": actual_loc_id,
                                "quantity": int(prod.stock_quantity or 0)
                            })
                            updated_inv_ids.add(inv_id)

                if shopify_product_id and price_updates:
                    price_mutation = """
                    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        productVariants { id price compareAtPrice } userErrors { field message }
                      }
                    }
                    """
                    res = await shopify_graphql(store.shop_domain, token, price_mutation, {"productId": shopify_product_id, "variants": price_updates})
                    user_errors = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                    if user_errors:
                        print(f"   ❌ Shopify Price Update Failed: {user_errors}", flush=True)
                    else:
                        print(f"   ✅ Shopify Price Updated", flush=True)

                if stock_updates:
                    try:
                        for i in range(0, len(stock_updates), 250):
                            chunk = stock_updates[i:i+250]
                            await _set_inventory_quantities(store.shop_domain, token, chunk)
                        print(f"   ✅ Shopify Stock Updated", flush=True)
                    except Exception as e:
                        print(f"   ⚠️ Shopify Stock update failed: {e}", flush=True)

            except Exception as e:
                print(f"❌ Error checking {product.asin}: {e}", flush=True)
                traceback.print_exc()
                try:
                    db.rollback()
                except Exception:
                    pass
    finally:
        db.close()
        print("\n✅ [CRON JOB] Sync Complete.\n", flush=True)