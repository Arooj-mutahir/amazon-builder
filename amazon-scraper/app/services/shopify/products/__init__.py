import asyncio
from ..client import shopify_graphql
from ..locations import get_primary_location, get_shopify_category_id, publish_product
from ..metafields import _build_description_with_metafields

from .stock_utils import _variant_stock, _resolve_parent_stock
from .pricing import _calculate_price
from .inventory import _set_inventory_quantities
from .media import _upload_media_and_get_id, _attach_variant_images

# ============================================
# CREATE SINGLE VARIANT PRODUCT
# ============================================
async def create_shopify_product(shop: str, access_token: str, product_data: dict) -> dict:
    print(f'🛠️  Creating Single-Variant Product: {product_data.get("title")}', flush=True)
    
    try:
        location_id = await get_primary_location(shop, access_token)
        amazon_categories = product_data.get('categories', []) or []
        shopify_category_id = await get_shopify_category_id(shop, access_token, amazon_categories) if amazon_categories else None
        
        create_mutation = """
        mutation productCreate($input: ProductInput!) {
          productCreate(input: $input) {
            product { id title handle }
            userErrors { field message }
          }
        }
        """

        raw_details = product_data.get("details", {})
        enhanced_description = _build_description_with_metafields(
            product_data.get("description", ""),
            product_data.get("bullets") or [],
            raw_details,
            product_data.get("size_chart"),
            product_data.get("reviews") or [],
        )

        input_data = {
            'title': product_data.get('title', 'Untitled')[:255],
            'descriptionHtml': enhanced_description,
            'vendor': product_data.get('brand', ''),
            'productType': product_data.get('product_type') or (amazon_categories[-1] if amazon_categories else "General"),
            'tags': ", ".join(product_data.get('tags', [])) if isinstance(product_data.get('tags'), list) else str(product_data.get('tags', '')),
            'status': 'DRAFT',
            'productOptions': [{'name': 'Title', 'values': [{'name': 'Default'}]}],
        }
        
        if shopify_category_id: 
            input_data['category'] = shopify_category_id

        result = await shopify_graphql(shop, access_token, create_mutation, {'input': input_data})
        
        if 'errors' in result:
            return result
            
        user_errors = result.get('data', {}).get('productCreate', {}).get('userErrors', [])
        if user_errors:
            return {'errors': user_errors}

        product_obj = result.get("data", {}).get("productCreate", {}).get("product", {})
        product_id = product_obj.get("id")
        
        if product_id:
            # ✅ 1. Images upload karein
            valid_images = []
            for img in product_data.get('images', []):
                if img and isinstance(img, str):
                    if not img.startswith("http"): img = "https://" + img
                    valid_images.append(img)
            
            if valid_images:
                print(f"🖼️  Uploading {len(valid_images)} images...", flush=True)
                media_mutation = """
                mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
                  productCreateMedia(productId: $productId, media: $media) {
                    media { id ... on MediaImage { image { url } } }
                    userErrors { field message }
                  }
                }
                """
                media_payload = [{"originalSource": url, "mediaContentType": "IMAGE"} for url in valid_images]
                media_res = await shopify_graphql(shop, access_token, media_mutation, {
                    "productId": product_id,
                    "media": media_payload
                })
                if 'errors' in media_res:
                    print(f"⚠️ Media upload error: {media_res['errors']}", flush=True)

            in_stock, stock_qty = _variant_stock(product_data, default_stock_qty=0)
            if stock_qty is None:
                stock_qty = 0
            
            # ✅ Default variant ko update karein
            get_variants_query = """
            query getProductVariants($id: ID!) {
              product(id: $id) {
                variants(first: 10) {
                  nodes { id sku inventoryItem { id } }
                }
              }
            }
            """
            variants_res = await shopify_graphql(shop, access_token, get_variants_query, {"id": product_id})
            existing_variants = (variants_res.get("data", {}).get("product", {}).get("variants", {}).get("nodes") or [])

            if existing_variants:
                first_variant_id = existing_variants[0]["id"]
                first_variant_inv_id = (existing_variants[0].get("inventoryItem") or {}).get("id")

                update_mutation = """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants { id sku }
                    userErrors { field message }
                  }
                }
                """
                await shopify_graphql(shop, access_token, update_mutation, {
                    "productId": product_id,
                    "variants": [{
                        "id": first_variant_id,
                        "price": str(product_data.get('price', '0.00')),
                        "inventoryItem": {
                            "tracked": True,
                            "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}},
                            "sku": product_data.get('asin', ''),
                        },
                        "optionValues": [{"name": 'Default', "optionName": 'Title'}],
                    }]
                })

                # ✅ Actual location fetch karein
                inv_loc_query = """
                query getInventoryItemLocations($id: ID!) {
                  inventoryItem(id: $id) {
                    inventoryLevels(first: 5) {
                      nodes { location { id name } }
                    }
                  }
                }
                """
                loc_res = await shopify_graphql(shop, access_token, inv_loc_query, {"id": first_variant_inv_id})
                inv_levels = (loc_res.get("data", {}).get("inventoryItem", {}).get("inventoryLevels", {}).get("nodes") or [])
                
                actual_location_id = location_id
                if inv_levels:
                    actual_location_id = inv_levels[0]["location"]["id"]
                    print(f"📍 Product actual location: {inv_levels[0]['location']['name']} ({actual_location_id})", flush=True)
                else:
                    print(f"⚠️ No inventory levels found. Using fallback: {location_id}", flush=True)

                # ✅ Stock set karein
                try:
                    if first_variant_inv_id and actual_location_id:
                        await _set_inventory_quantities(shop, access_token, [{
                            "inventoryItemId": first_variant_inv_id,
                            "locationId": actual_location_id,
                            "quantity": int(stock_qty)
                        }])
                except Exception as e:
                    print(f"⚠️ Inventory set failed (Single): {e}", flush=True)

            await publish_product(shop, access_token, product_id)
            
        return result
        
    except Exception as e:
        print(f"❌ Exception in create_shopify_product: {e}", flush=True)
        return {"errors": [{"message": str(e)}]}


# ============================================
# CREATE MULTI-VARIANT PRODUCT
# ============================================
async def create_shopify_product_with_variants(shop, access_token, product_data, variants_raw, markup_val, markup_type, extra_percent, tax_rate) -> dict:
    if not variants_raw:
        return await create_shopify_product(shop, access_token, product_data)
        
    print(f'🛠️  Creating Multi-Variant Product: {len(variants_raw)} variants', flush=True)
    
    try:
        location_id = await get_primary_location(shop, access_token)
        parent_stock_qty = _resolve_parent_stock(product_data, default_stock_qty=0)
        
        per_variant_options = []
        for idx, v_raw in enumerate(variants_raw):
            opt_values = {}
            clean_ov = v_raw.get("option_values") or []
            for ov in clean_ov:
                if ov.get("name") and ov.get("value"):
                    opt_values[str(ov["name"])] = str(ov["value"]).strip()
            per_variant_options.append({
                "index": idx, 
                "asin": v_raw.get("asin") or f"variant-{idx}", 
                "opts": opt_values, 
                "images": v_raw.get("images") or [] 
            })

        option_names = []
        for entry in per_variant_options:
            for name in entry["opts"].keys():
                if name not in option_names: option_names.append(name)
        if not option_names: option_names = ["Title"]

        for entry in per_variant_options:
            for name in option_names:
                if not entry["opts"].get(name): entry["opts"][name] = f"Variant-{entry['asin'][-6:]}"

        product_options = []
        for name in option_names:
            values, seen = [], set()
            for entry in per_variant_options:
                val = entry["opts"][name]
                if val not in seen:
                    seen.add(val); values.append({"name": val})
            product_options.append({"name": name, "values": values})

        gallery_urls, gallery_seen = [], set()
        def _register(url):
            if not url or not isinstance(url, str): return
            url = url.strip()
            if not url.startswith("http"): url = "https://" + url
            if url not in gallery_seen: gallery_seen.add(url); gallery_urls.append(url)

        for img in (product_data.get('images') or []):
            _register(img)
        for entry in per_variant_options:
            for img in (entry.get("images") or []):
                _register(img)

        amazon_categories = product_data.get('categories', []) or []
        prod_type = product_data.get('product_type') or (amazon_categories[-1] if amazon_categories else "General")
        
        enhanced_description = _build_description_with_metafields(
            product_data.get("description", ""),
            product_data.get("bullets") or [],
            product_data.get("details", {}),
            product_data.get("size_chart"),
            product_data.get("reviews") or [],
        )

        create_mutation = """
        mutation productCreate($input: ProductInput!) {
          productCreate(input: $input) {
            product { id title handle }
            userErrors { field message }
          }
        }
        """

        input_data = {
            'title': (product_data.get('title') or 'Untitled')[:255],
            'descriptionHtml': enhanced_description,
            'vendor': product_data.get('brand', ''),
            'productType': prod_type,
            'tags': ", ".join(product_data.get('tags', [])) if isinstance(product_data.get('tags'), list) else str(product_data.get('tags', '')),
            'status': 'DRAFT',
            'productOptions': product_options,
        }

        if amazon_categories:
            shopify_category_id = await get_shopify_category_id(shop, access_token, amazon_categories)
            if shopify_category_id:
                input_data['category'] = shopify_category_id

        result = await shopify_graphql(shop, access_token, create_mutation, {'input': input_data})
        
        if 'errors' in result:
            return result
            
        user_errors = result.get('data', {}).get('productCreate', {}).get('userErrors', [])
        if user_errors:
            return {'errors': user_errors}

        product_obj = result.get('data', {}).get('productCreate', {}).get('product') or {}
        product_id = product_obj.get('id')

        if product_id:
            # ✅ 1. Images upload karein
            if gallery_urls:
                print(f"🖼️  Uploading {len(gallery_urls)} images...", flush=True)
                media_mutation = """
                mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
                  productCreateMedia(productId: $productId, media: $media) {
                    media { id ... on MediaImage { image { url } } }
                    userErrors { field message }
                  }
                }
                """
                media_payload = [{"originalSource": url, "mediaContentType": "IMAGE"} for url in gallery_urls]
                await shopify_graphql(shop, access_token, media_mutation, {
                    "productId": product_id,
                    "media": media_payload
                })

            # ✅ 2. Pehle default variant ko update karein
            get_variants_query = """
            query getProductVariants($id: ID!) {
              product(id: $id) {
                variants(first: 10) {
                  nodes { id sku inventoryItem { id } }
                }
              }
            }
            """
            variants_res = await shopify_graphql(shop, access_token, get_variants_query, {"id": product_id})
            existing_variants = (variants_res.get("data", {}).get("product", {}).get("variants", {}).get("nodes") or [])

            if existing_variants:
                first_variant_id = existing_variants[0]["id"]
                first_variant_inv_id = (existing_variants[0].get("inventoryItem") or {}).get("id")
                
                first_v_raw = variants_raw[0]
                first_entry = per_variant_options[0]
                first_price = float(first_v_raw.get("price", 0.0) or 0.0)
                first_final_price = _calculate_price(first_price, markup_val, markup_type, extra_percent, tax_rate)
                first_option_values = [{"name": first_entry["opts"][name], "optionName": name} for name in option_names]
                
                update_mutation = """
                mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants { id sku }
                    userErrors { field message }
                  }
                }
                """
                await shopify_graphql(shop, access_token, update_mutation, {
                    "productId": product_id,
                    "variants": [{
                        "id": first_variant_id,
                        "price": str(first_final_price),
                        "inventoryItem": {
                            "tracked": True,
                            "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}},
                            "sku": first_v_raw.get("asin", ""),
                        },
                        "optionValues": first_option_values,
                    }]
                })

            # ✅ 3. Baqi variants create karein
            shopify_variants = []
            for idx, v_raw in enumerate(variants_raw):
                if idx == 0:
                    continue
                entry = per_variant_options[idx]
                price = float(v_raw.get("price", 0.0) or 0.0)
                v_final_price = _calculate_price(price, markup_val, markup_type, extra_percent, tax_rate)
                
                option_values_payload = [{"name": entry["opts"][name], "optionName": name} for name in option_names]

                shopify_variants.append({
                    "price": str(v_final_price),
                    "inventoryItem": {
                        "tracked": True,
                        "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}},
                        "sku": v_raw.get("asin", ""),
                    },
                    "optionValues": option_values_payload,
                })

            if shopify_variants:
                variants_mutation = """
                mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                  productVariantsBulkCreate(productId: $productId, variants: $variants) {
                    productVariants { id sku inventoryItem { id sku } }
                    userErrors { field message }
                  }
                }
                """
                
                var_result = await shopify_graphql(shop, access_token, variants_mutation, {
                    "productId": product_id,
                    "variants": shopify_variants
                })
                
                if 'errors' in var_result:
                    print(f"❌ Variants GraphQL Error: {var_result['errors']}", flush=True)
                    return {"errors": var_result['errors']}

                var_user_errors = var_result.get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors", [])
                if var_user_errors:
                    print(f"❌ Variants User Errors: {var_user_errors}", flush=True)
                    return {"errors": var_user_errors}

                # ✅ Har variant ki actual location fetch karein aur stock set karein
                created_variants = var_result.get("data", {}).get("productVariantsBulkCreate", {}).get("productVariants", [])
                
                for cv in created_variants:
                    inv_item = cv.get("inventoryItem") or {}
                    sku = inv_item.get("sku")
                    inv_id = inv_item.get("id")
                    if not inv_id:
                        continue
                    
                    # ✅ Product ki actual location fetch karein
                    inv_loc_query = """
                    query getInventoryItemLocations($id: ID!) {
                      inventoryItem(id: $id) {
                        inventoryLevels(first: 5) {
                          nodes { location { id name } }
                        }
                      }
                    }
                    """
                    loc_res = await shopify_graphql(shop, access_token, inv_loc_query, {"id": inv_id})
                    inv_levels = (loc_res.get("data", {}).get("inventoryItem", {}).get("inventoryLevels", {}).get("nodes") or [])
                    
                    actual_location_id = location_id
                    if inv_levels:
                        actual_location_id = inv_levels[0]["location"]["id"]
                        print(f"📍 Variant {sku} actual location: {inv_levels[0]['location']['name']}", flush=True)
                    
                    for v_raw in variants_raw:
                        if v_raw.get("asin") == sku:
                            variant_stock = int(v_raw.get("stock_qty") or parent_stock_qty or 0)
                            try:
                                await _set_inventory_quantities(shop, access_token, [{
                                    "inventoryItemId": inv_id,
                                    "locationId": actual_location_id,
                                    "quantity": variant_stock
                                }])
                            except Exception as e:
                                print(f"⚠️ Inventory set failed for {sku}: {e}", flush=True)
                            break

            # ✅ 4. Images ko variants ke sath attach karein
            media_query = """
            query getProductMedia($id: ID!) {
              product(id: $id) {
                media(first: 250) { nodes { id ... on MediaImage { image { url } } } }
                variants(first: 100) { nodes { id sku } }
              }
            }
            """
            media_result = await shopify_graphql(shop, access_token, media_query, {"id": product_id})
            refreshed_product = (media_result.get("data") or {}).get("product") or {}
            fresh_media = (refreshed_product.get("media") or {}).get("nodes") or []
            fresh_variants = (refreshed_product.get("variants") or {}).get("nodes") or []

            await _attach_variant_images(shop, access_token, product_id, fresh_media, fresh_variants, per_variant_options, gallery_urls)

            await publish_product(shop, access_token, product_id)

        return result
    except Exception as e:
        print(f"❌ Exception in create_shopify_product_with_variants: {e}", flush=True)
        return {"errors": [{"message": str(e)}]}