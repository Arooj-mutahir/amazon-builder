import asyncio
from ..client import shopify_graphql
from ..locations import get_primary_location, get_shopify_category_id, publish_product
from ..metafields import _build_description_with_metafields

# ✅ Import from new modules
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
        if shopify_category_id:
            print(f"✅ Shopify Category ID set: {shopify_category_id}", flush=True)

        mutation = """
        mutation productSet($input: ProductSetInput!) {
          productSet(input: $input) {
            product { 
              id title handle 
              media(first: 100) { nodes { id ... on MediaImage { image { url } } } }
              variants(first: 10) { nodes { id sku inventoryItem { id } } } 
            }
            userErrors { field message }
          }
        }
        """

        valid_images = []
        for img in product_data.get('images', []):
            if img and isinstance(img, str):
                if not img.startswith("http"): img = "https://" + img
                valid_images.append({'originalSource': img})

        in_stock, stock_qty = _variant_stock(product_data, default_stock_qty=0)
        if stock_qty is None:
            stock_qty = 0
        print(f"📦 Stock resolved: in_stock={in_stock}, qty={stock_qty}", flush=True)

        inventory_quantities = [{'locationId': location_id, 'name': 'available', 'quantity': int(stock_qty)}] if location_id else []

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
            'status': 'ACTIVE',
            'productOptions': [{'name': 'Title', 'values': [{'name': 'Default'}]}],
            'variants': [
                {
                    'price': str(product_data.get('price', '0.00')),
                    'sku': product_data.get('asin', ''),
                    'inventoryItem': {'tracked': True, 'measurement': {'weight': {'value': 0.5, 'unit': 'KILOGRAMS'}}},
                    'inventoryQuantities': inventory_quantities,
                    'optionValues': [{'name': 'Default', 'optionName': 'Title'}]
                }
            ]
        }
        
        if valid_images: input_data['files'] = valid_images
        if shopify_category_id: input_data['category'] = shopify_category_id

        print(f"📡 Sending productSet request to Shopify...", flush=True)
        result = await shopify_graphql(shop, access_token, mutation, {'input': input_data})
        
        print(f"🔍 SHOPIFY RESPONSE: {result}", flush=True)

        if 'errors' in result:
            return result
            
        user_errors = result.get('data', {}).get('productSet', {}).get('userErrors', [])
        if user_errors:
            return {'errors': user_errors}

        product_obj = result.get("data", {}).get("productSet", {}).get("product", {})
        product_id = product_obj.get("id")
        
        if product_id:
            try:
                await shopify_graphql(shop, access_token, """
                mutation productUpdate($input: ProductInput!) {
                  productUpdate(input: $input) {
                    userErrors { field message }
                  }
                }
                """, {"input": {"id": product_id, "descriptionHtml": enhanced_description}})
                print("✅ Description force-updated (Single)!", flush=True)
            except Exception as e:
                print(f"⚠️ Description update failed: {e}", flush=True)

            print("⏳ Waiting 8 seconds for Shopify to process images...", flush=True)
            await asyncio.sleep(8) 
            media_nodes = (product_obj.get('media') or {}).get('nodes') or []
            variant_nodes = (product_obj.get('variants') or {}).get('nodes') or []
            if valid_images and media_nodes and variant_nodes:
                clean_url = valid_images[0]['originalSource'].split('?')[0]
                for m in media_nodes:
                    if m.get('image') and m['image'].get('url') and m['image']['url'].split('?')[0] == clean_url:
                        await shopify_graphql(shop, access_token, """
                        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                            userErrors { field message }
                          }
                        }
                        """, {"productId": product_id, "variants": [{"id": variant_nodes[0]['id'], "mediaId": m['id']}]})
                        break

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

        # 1. ProductCreate mutation (Simple product create karein)
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
            'status': 'DRAFT',  # DRAFT mein rakhein
            'productOptions': product_options,
        }

        if amazon_categories:
            shopify_category_id = await get_shopify_category_id(shop, access_token, amazon_categories)
            if shopify_category_id:
                input_data['category'] = shopify_category_id

        print(f"📡 Sending productCreate request...", flush=True)
        result = await shopify_graphql(shop, access_token, create_mutation, {'input': input_data})
        
        print(f"🔍 CREATE RESPONSE: {result}", flush=True)

        if 'errors' in result:
            return result
            
        user_errors = result.get('data', {}).get('productCreate', {}).get('userErrors', [])
        if user_errors:
            return {'errors': user_errors}

        product_obj = result.get('data', {}).get('productCreate', {}).get('product') or {}
        product_id = product_obj.get('id')

        # 2. Ab variants add karein (productVariantsBulkCreate)
        if product_id:
            shopify_variants = []
            for idx, v_raw in enumerate(variants_raw):
                entry = per_variant_options[idx]
                price = float(v_raw.get("price", 0.0) or 0.0)
                v_final_price = _calculate_price(price, markup_val, markup_type, extra_percent, tax_rate)
                
                option_values_payload = [{"name": entry["opts"][name], "optionName": name} for name in option_names]

                shopify_variants.append({
                    "price": str(v_final_price),
                    "sku": v_raw.get("asin", ""),
                    "inventoryItem": {"tracked": True, "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}}},
                    "optionValues": option_values_payload,
                })

            variants_mutation = """
            mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
              productVariantsBulkCreate(productId: $productId, variants: $variants) {
                productVariants { id sku inventoryItem { id } }
                userErrors { field message }
              }
            }
            """
            
            var_result = await shopify_graphql(shop, access_token, variants_mutation, {
                "productId": product_id,
                "variants": shopify_variants
            })
            
            print(f"🔍 VARIANTS RESPONSE: {var_result}", flush=True)

            # 3. Inventory set karein
            created_variants = var_result.get("data", {}).get("productVariantsBulkCreate", {}).get("productVariants", [])
            stock_updates = []
            for cv in created_variants:
                sku = cv.get("sku")
                inv_id = (cv.get("inventoryItem") or {}).get("id")
                for idx, v_raw in enumerate(variants_raw):
                    if v_raw.get("asin") == sku:
                        variant_stock = int(v_raw.get("stock_qty") or parent_stock_qty or 0)
                        stock_updates.append({"inventoryItemId": inv_id, "locationId": location_id, "quantity": variant_stock})
                        break
            
            if stock_updates:
                await _set_inventory_quantities(shop, access_token, stock_updates)

            # 4. Images ko upload karein (alag mutation)
            # (Yeh aapke _attach_variant_images function mein handle ho jata hai)

            # 5. Product ko publish karein
            await publish_product(shop, access_token, product_id)

        return result
    except Exception as e:
        print(f"❌ Exception in create_shopify_product_with_variants: {e}", flush=True)
        return {"errors": [{"message": str(e)}]}