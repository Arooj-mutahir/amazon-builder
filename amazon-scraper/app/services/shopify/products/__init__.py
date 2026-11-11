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

        mutation = """
        mutation productSet($input: ProductSetInput!) {
          productSet(input: $input) {
            product { 
              id title handle 
              media(first: 250) { nodes { id ... on MediaImage { image { url } } } } 
              variants(first: 100) { nodes { id sku inventoryItem { id } } } 
            }
            userErrors { field message }
          }
        }
        """

        shopify_variants = []
        for idx, v_raw in enumerate(variants_raw):
            entry = per_variant_options[idx]
            price = float(v_raw.get("price", 0.0) or 0.0)
            v_final_price = _calculate_price(price, markup_val, markup_type, extra_percent, tax_rate)

            variant_stock = int(v_raw.get("stock_qty") or parent_stock_qty or 0)
            v_inventory_quantities = [{'locationId': location_id, 'name': 'available', 'quantity': variant_stock}] if location_id else []
            
            option_values_payload = [{"name": entry["opts"][name], "optionName": name} for name in option_names]

            shopify_variants.append({
                "price": str(v_final_price), 
                "sku": v_raw.get("asin", ""),
                "inventoryItem": {"tracked": True, "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}}},
                "inventoryQuantities": v_inventory_quantities,
                "optionValues": option_values_payload,
            })

        amazon_categories = product_data.get('categories', []) or []
        prod_type = product_data.get('product_type') or (amazon_categories[-1] if amazon_categories else "General")
        
        enhanced_description = _build_description_with_metafields(
            product_data.get("description", ""),
            product_data.get("bullets") or [],
            product_data.get("details", {}),
            product_data.get("size_chart"),
            product_data.get("reviews") or [],
        )

        input_data = {
            'title': (product_data.get('title') or 'Untitled')[:255],
            'descriptionHtml': enhanced_description,
            'vendor': product_data.get('brand', ''),
            'productType': prod_type,
            'tags': ", ".join(product_data.get('tags', [])) if isinstance(product_data.get('tags'), list) else str(product_data.get('tags', '')),
            'status': 'ACTIVE',
            'productOptions': product_options,
            'variants': shopify_variants,
        }
        if gallery_urls: input_data['files'] = [{'originalSource': u} for u in gallery_urls]

        if amazon_categories:
            shopify_category_id = await get_shopify_category_id(shop, access_token, amazon_categories)
            if shopify_category_id:
                input_data['category'] = shopify_category_id

        result = await shopify_graphql(shop, access_token, mutation, {'input': input_data})
        
        if 'errors' in result:
            return result
            
        user_errors = result.get('data', {}).get('productSet', {}).get('userErrors', [])
        if user_errors:
            return {'errors': user_errors}

        product_obj = result.get('data', {}).get('productSet', {}).get('product') or {}
        product_id = product_obj.get('id')
        
        if product_id:
            try:
                await shopify_graphql(shop, access_token, """
                mutation productUpdate($input: ProductInput!) {
                  productUpdate(input: $input) {
                    userErrors { field message }
                  }
                }
                """, {"input": {"id": product_id, "descriptionHtml": enhanced_description}})
                print("✅ Description force-updated (Multi)!", flush=True)
            except Exception as e:
                print(f"⚠️ Description update failed: {e}", flush=True)

            await asyncio.sleep(6) 

            try:
                price_updates = []
                for idx, v_raw in enumerate(variants_raw):
                    price = float(v_raw.get("price", 0.0) or 0.0)
                    v_final_price = _calculate_price(price, markup_val, markup_type, extra_percent, tax_rate)
                    for v_node in (product_obj.get('variants') or {}).get('nodes') or []:
                        if v_node.get("sku") == v_raw.get("asin"):
                            price_updates.append({"id": v_node["id"], "price": str(v_final_price)})
                            break
                
                if price_updates:
                    price_mutation = """
                    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                        userErrors { field message }
                      }
                    }
                    """
                    await shopify_graphql(shop, access_token, price_mutation, {"productId": product_id, "variants": price_updates})
            except Exception as e:
                print(f"⚠️ Failed to update exact prices on create: {e}", flush=True)

            try:
                stock_updates = []
                for idx, v_raw in enumerate(variants_raw):
                    variant_stock = int(v_raw.get("stock_qty") or parent_stock_qty or 0)
                    for v_node in (product_obj.get('variants') or {}).get('nodes') or []:
                        if v_node.get("sku") == v_raw.get("asin"):
                            inv_id = (v_node.get('inventoryItem') or {}).get('id')
                            if inv_id:
                                stock_updates.append({"inventoryItemId": inv_id, "locationId": location_id, "quantity": int(variant_stock)})
                            break
                if stock_updates:
                    await _set_inventory_quantities(shop, access_token, stock_updates)
            except Exception as e:
                print(f"⚠️ Failed to set stock on create: {e}", flush=True)

            try:
                media_query = """
                query getProductMedia($id: ID!) {
                  product(id: $id) {
                    media(first: 250) { nodes { id ... on MediaImage { image { url } } } }
                    variants(first: 100) { nodes { id sku inventoryItem { id } } }
                  }
                }
                """
                media_result = await shopify_graphql(shop, access_token, media_query, {"id": product_id})
                refreshed_product = (media_result.get("data") or {}).get("product") or {}
                fresh_media   = (refreshed_product.get("media")    or {}).get("nodes") or []
                fresh_variants= (refreshed_product.get("variants") or {}).get("nodes") or []
            except Exception as e:
                fresh_media    = (product_obj.get('media')    or {}).get('nodes') or []
                fresh_variants = (product_obj.get('variants') or {}).get('nodes') or []

            await _attach_variant_images(shop, access_token, product_id, fresh_media, fresh_variants, per_variant_options, gallery_urls)
            await publish_product(shop, access_token, product_id)

        return result
    except Exception as e:
        print(f"❌ Exception in create_shopify_product_with_variants: {e}", flush=True)
        return {"errors": [{"message": str(e)}]}