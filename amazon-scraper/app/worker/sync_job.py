# app/worker/sync_job.py
import traceback
import asyncio
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

# ✅ NAYA: Har product ka actual location fetch karne ke liye
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


async def sync_prices_job():
    print("\n⏰ [CRON JOB] Starting Price + Stock Sync...", flush=True)
    
    from app.api.routes.shopify.helpers import calculate_final_price, _get_valid_access_token
    
    db = SessionLocal()
    try:
        products = db.query(Product).filter(
            Product.shopify_product_id.isnot(None),
            Product.is_variation == False
        ).all()
        print(f"🔍 Found {len(products)} parent products to check.\n", flush=True)

        for product in products:
            try:
                store = db.query(ShopifyStore).filter(ShopifyStore.id == product.shopify_store_id).first()
                if not store:
                    continue

                print(f"=======================================================", flush=True)
                print(f"🔎 Checking Parent ASIN: {product.asin} (Shopify ID: {product.shopify_product_id})", flush=True)

                store_markup = float(store.default_markup if store.default_markup is not None else 0.0)
                store_markup_type = str(store.default_markup_type or "fixed").lower()
                store_extra = float(store.default_extra_percent if store.default_extra_percent is not None else 0.0)
                store_tax = float(store.default_tax_rate if store.default_tax_rate is not None else 0.0)
                default_stock = int(getattr(store, "default_stock_qty", 0) or 0)

                markup_display = f"${store_markup:.2f}" if store_markup_type == "fixed" else f"{store_markup}%"
                print(f"   ⚙️  UI Settings (Store #{store.id}): Type={store_markup_type.upper()} | Markup={markup_display} | Extra={store_extra}% | Tax={store_tax}%", flush=True)

                child_products = db.query(Product).filter(
                    Product.parent_asin == product.asin,
                    Product.is_variation == True
                ).all()
                all_products = [product] + child_products
                print(f"   📦 Total variants to sync: {len(all_products)} (1 Parent + {len(child_products)} Children)", flush=True)

                scrape_timeout = max(60.0, float(len(child_products) * 3.5 + 30.0))
                try:
                    latest_data = await asyncio.wait_for(
                        get_shopify_product_data(product.asin, default_stock_qty=default_stock, fetch_all_variants=True),
                        timeout=scrape_timeout
                    )
                except asyncio.TimeoutError:
                    print(f"   ⏳ Timeout ({scrape_timeout:.0f}s) fetching Amazon data for {product.asin}, skipping...", flush=True)
                    continue
                except Exception as e:
                    print(f"   ⚠️ Scrape failed for {product.asin}: {e}", flush=True)
                    continue

                latest_amazon_price = float(latest_data.get("price") or 0.0)
                
                # ✅ FIX 1: Agar price 0 hai toh skip karein (Shopify par 0 na chala jaye)
                if latest_amazon_price <= 0:
                    print(f"   ⏭️ Skipping {product.asin} (Amazon Price is $0.00 or unavailable)", flush=True)
                    continue

                latest_parent_stock = latest_data.get("stock_qty")
                latest_parent_available = _get_availability(latest_data)
                resolved_parent_stock = _resolve_stock(latest_parent_available, latest_parent_stock, default_stock)

                variants_by_asin = {v["asin"]: v for v in (latest_data.get("variant_products") or []) if v.get("asin")}

                print(f"   💰 Calculating prices & updating Database...", flush=True)
                for prod in all_products:
                    if prod.asin == product.asin:
                        v_amazon_price = latest_amazon_price
                        v_available = latest_parent_available
                        v_stock = resolved_parent_stock
                    else:
                        v_data = variants_by_asin.get(prod.asin) or {}
                        fetched_p = v_data.get("price")
                        v_amazon_price = float(fetched_p) if (fetched_p and float(fetched_p) > 0) else latest_amazon_price
                        
                        v_available = _get_availability(v_data) if (v_data.get("in_stock") is not None or v_data.get("is_available") is not None) else latest_parent_available
                        v_raw_stock = v_data.get("stock_qty") if v_data.get("stock_qty") is not None else latest_parent_stock
                        v_stock = _resolve_stock(v_available, v_raw_stock, default_stock)

                    if v_amazon_price > 0:
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
                    print(f"      👉 ASIN {prod.asin} ({v_type_label}): Amazon=${v_amazon_price:.2f} -> UI Final=${prod.price:.2f} | Stock={prod.stock_quantity} ({prod.availability})", flush=True)

                db.commit()
                print(f"   💾 Database updated successfully.", flush=True)

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
                        print(f"   ⚠️ Product {shopify_product_id} not found by ID. Searching by SKU {product.asin}...", flush=True)
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
                            db.commit()

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
                
                # Store ka default location (fallback)
                default_location_id = getattr(store, "shopify_location_id", None) or await _get_primary_location_cached(store, db)

                for prod in all_products:
                    fresh_v_id = fresh_variant_map.get(prod.asin)
                    if fresh_v_id and prod.price:
                        price_updates.append({"id": fresh_v_id, "price": f"{prod.price:.2f}"})

                    inv_id = fresh_inventory_map.get(prod.asin)
                    if inv_id and inv_id not in updated_inv_ids:
                        # ✅ FIX 2: Product ka ACTUAL location fetch karein
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
                        productVariants { id price } userErrors { field message }
                      }
                    }
                    """
                    res = await shopify_graphql(store.shop_domain, token, price_mutation, {"productId": shopify_product_id, "variants": price_updates})
                    user_errors = res.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
                    if user_errors:
                        print(f"   ❌ Shopify Price Update Failed for {product.asin}: {user_errors}", flush=True)

                if stock_updates:
                    try:
                        for i in range(0, len(stock_updates), 250):
                            chunk = stock_updates[i:i+250]
                            await _set_inventory_quantities(store.shop_domain, token, chunk)
                    except Exception as e:
                        print(f"   ⚠️ Shopify Stock update failed: {e}", flush=True)

            except Exception as e:
                print(f"❌ Error checking {product.asin}: {e}", flush=True)
                traceback.print_exc()
                db.rollback()
    finally:
        db.close()
        print("\n✅ [CRON JOB] Sync Complete.\n", flush=True)