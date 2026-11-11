import os

NEW_CODE = '''# ============================================
# app/services/shopify.py
# v8 — Per-variant images via filename-match (mediaId)
# ============================================

import logging
import hmac as _hmac
import hashlib
import base64
import json
import uuid
import re
from urllib.parse import urlencode, quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _api_version() -> str:
    return getattr(settings, "SHOPIFY_API_VERSION", "2024-04")


def _build_description_with_metafields(raw_description: str, raw_details: dict) -> str:
    if not raw_details:
        return raw_description
    rows = []
    weight = raw_details.get("item_weight") or raw_details.get("package_weight")
    dims = raw_details.get("item_dimensions") or raw_details.get("product_dimensions") or raw_details.get("package_dimensions")
    material = raw_details.get("material_type") or raw_details.get("material")
    color = raw_details.get("color")
    country = raw_details.get("country_of_origin")
    model = raw_details.get("item_model_number")
    if weight:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Item Weight</strong></td><td style='padding: 8px;'>{weight}</td></tr>")
    if dims:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Dimensions</strong></td><td style='padding: 8px;'>{dims}</td></tr>")
    if material:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Material</strong></td><td style='padding: 8px;'>{material}</td></tr>")
    if color:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Color</strong></td><td style='padding: 8px;'>{color}</td></tr>")
    if country:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Origin</strong></td><td style='padding: 8px;'>{country}</td></tr>")
    if model:
        rows.append(f"<tr><td style='padding: 8px;'><strong>Model</strong></td><td style='padding: 8px;'>{model}</td></tr>")
    if not rows:
        return raw_description
    table_html = f"""
    <div style="margin-top: 30px;">
        <h3>Product Specifications</h3>
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #ddd;">
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """
    return (raw_description or "") + table_html


async def shopify_graphql(shop: str, token: str, query: str, variables: dict = None) -> dict:
    url = f"https://{shop}/admin/api/{_api_version()}/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code in (401, 403):
                return {"errors": [{"status": response.status_code, "message": response.text}]}
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.exception(f"shopify_graphql exception: {e}")
        return {"errors": [{"message": str(e)}]}


def build_auth_url(shop: str) -> str:
    api_key = getattr(settings, "SHOPIFY_API_KEY", "")
    scopes = getattr(settings, "SHOPIFY_SCOPES", "read_products,write_products")
    redirect_uri = getattr(settings, "SHOPIFY_REDIRECT_URI", "")
    state = str(uuid.uuid4())
    params = {"client_id": api_key, "scope": scopes, "redirect_uri": redirect_uri, "state": state}
    return f"https://{shop}/admin/oauth/authorize?{urlencode(params)}"


async def exchange_code_for_token(shop: str, code: str) -> dict:
    api_key = getattr(settings, "SHOPIFY_API_KEY", "")
    api_secret = getattr(settings, "SHOPIFY_API_SECRET", "")
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": api_key, "client_secret": api_secret, "code": code}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.exception(f"exchange_code_for_token failed: {e}")
        return {}


async def refresh_shopify_token(shop: str, refresh_token: str) -> dict:
    api_key = getattr(settings, "SHOPIFY_API_KEY", "")
    api_secret = getattr(settings, "SHOPIFY_API_SECRET", "")
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": api_key, "client_secret": api_secret, "grant_type": "refresh_token", "refresh_token": refresh_token}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload)
            if r.status_code != 200:
                return {}
            return r.json()
    except Exception:
        return {}


def verify_hmac(query_params: dict) -> bool:
    api_secret = getattr(settings, "SHOPIFY_API_SECRET", "")
    if not api_secret:
        return False
    hmac_received = query_params.get("hmac", "")
    if not hmac_received:
        return False
    params = {k: v for k, v in query_params.items() if k not in ("hmac", "signature")}
    sorted_qs = "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in sorted(params.items()))
    digest = _hmac.new(api_secret.encode(), sorted_qs.encode(), hashlib.sha256).hexdigest()
    return _hmac.compare_digest(digest, hmac_received)


def verify_id_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(payload_b64))
    except Exception:
        return {}


async def exchange_id_token_for_offline_token(shop: str, id_token: str) -> dict:
    api_key = getattr(settings, "SHOPIFY_API_KEY", "")
    api_secret = getattr(settings, "SHOPIFY_API_SECRET", "")
    url = f"https://{shop}/admin/oauth/access_token"
    payload = {"client_id": api_key, "client_secret": api_secret, "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange", "subject_token": id_token, "subject_token_type": "urn:ietf:params:oauth:token-type:id_token", "requested_token_type": "urn:shopify:params:oauth:token-type:offline-access-token"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            return r.json()
    except Exception:
        return {}


async def get_shopify_category_id(shop: str, access_token: str, amazon_categories: list) -> str:
    if not amazon_categories:
        return None
    search_query = amazon_categories[-1].replace("&", "").strip()
    query = """
    query getCategory($search: String!) {
      taxonomy {
        categories(first: 1, search: $search) {
          edges { node { id } }
        }
      }
    }
    """
    result = await shopify_graphql(shop, access_token, query, {"search": search_query})
    try:
        edges = result.get('data', {}).get('taxonomy', {}).get('categories', {}).get('edges', [])
        if edges:
            return edges[0]['node']['id']
    except Exception:
        pass
    return None


async def publish_product(shop: str, access_token: str, product_id: str) -> dict:
    print(f"📢 Publishing product {product_id}...", flush=True)
    query_pub = """
    query getPublications {
      publications(first: 10) {
        edges { node { id name } }
      }
    }
    """
    pub_res = await shopify_graphql(shop, access_token, query_pub)
    if "errors" in pub_res:
        return pub_res
    publications = pub_res.get("data", {}).get("publications", {}).get("edges", [])
    online_store_id = None
    for pub in publications:
        if pub["node"]["name"] == "Online Store":
            online_store_id = pub["node"]["id"]
            break
    if not online_store_id:
        return {"success": False, "message": "Online Store not found"}
    mutation = """
    mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) {
        userErrors { field message }
      }
    }
    """
    variables = {"id": product_id, "input": [{"publicationId": online_store_id}]}
    result = await shopify_graphql(shop, access_token, mutation, variables)
    if "errors" in result:
        return result
    user_errors = result.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
    if user_errors:
        return {"errors": user_errors}
    print(f"✅ Published!", flush=True)
    return result


async def fetch_all_collections(shop: str, access_token: str) -> list:
    query = """
    query getCollections($cursor: String) {
      collections(first: 50, after: $cursor) {
        edges { node { id title handle } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    collections = []
    has_next = True
    cursor = None
    while has_next:
        result = await shopify_graphql(shop, access_token, query, {"cursor": cursor})
        if "errors" in result:
            break
        data = result.get("data", {}).get("collections", {})
        for edge in data.get("edges", []):
            node = edge.get("node", {})
            collections.append({"id": node.get("id"), "title": node.get("title"), "handle": node.get("handle")})
        page_info = data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
    return collections


async def add_product_to_collections(shop: str, access_token: str, product_id: str, collection_ids: list) -> dict:
    if not collection_ids:
        return {"success": True}
    mutation = """
    mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
      collectionAddProducts(id: $id, productIds: $productIds) {
        userErrors { field message }
      }
    }
    """
    all_ok = True
    for cid in collection_ids:
        res = await shopify_graphql(shop, access_token, mutation, {"id": cid, "productIds": [product_id]})
        if res.get("errors") or res.get("data", {}).get("collectionAddProducts", {}).get("userErrors"):
            all_ok = False
    return {"success": all_ok}


async def create_shopify_product(shop: str, access_token: str, product_data: dict) -> dict:
    location_id = "gid://shopify/Location/104777056292"
    amazon_categories = product_data.get('categories', [])
    shopify_category_id = await get_shopify_category_id(shop, access_token, amazon_categories) if amazon_categories else None
    mutation = """
    mutation productSet($input: ProductSetInput!) {
      productSet(input: $input) {
        product { id title handle }
        userErrors { field message }
      }
    }
    """
    valid_images = []
    for img in product_data.get('images', []):
        if img and isinstance(img, str):
            if not img.startswith("http"):
                img = "https://" + img
            valid_images.append({'originalSource': img})
    inventory_quantities = [{'locationId': location_id, 'name': 'available', 'quantity': 100}] if location_id else []
    raw_details = product_data.get("details", {})
    enhanced_description = _build_description_with_metafields(product_data.get("description", ""), raw_details)
    input_data = {
        'title': product_data.get('title', 'Untitled')[:255],
        'descriptionHtml': enhanced_description,
        'vendor': product_data.get('brand', ''),
        'productType': product_data.get('product_type') or (amazon_categories[-1] if amazon_categories else "General"),
        'tags': product_data.get('tags', []),
        'status': 'ACTIVE',
        'productOptions': [{'name': 'Title', 'values': [{'name': 'Default'}]}],
        'variants': [{'price': str(product_data.get('price', '0.00')), 'sku': product_data.get('asin', ''), 'inventoryItem': {'tracked': True, 'measurement': {'weight': {'value': 0.5, 'unit': 'KILOGRAMS'}}}, 'inventoryQuantities': inventory_quantities, 'optionValues': [{'name': 'Default', 'optionName': 'Title'}]}]
    }
    if valid_images:
        input_data['files'] = valid_images
    if shopify_category_id:
        input_data['category'] = shopify_category_id
    result = await shopify_graphql(shop, access_token, mutation, {'input': input_data})
    if 'errors' in result:
        return result
    user_errors = result.get('data', {}).get('productSet', {}).get('userErrors', [])
    if user_errors:
        return {'errors': user_errors}
    try:
        product_id = result.get("data", {}).get("productSet", {}).get("product", {}).get("id")
        if product_id:
            await publish_product(shop, access_token, product_id)
    except Exception as e:
        print(f"Auto-publish failed: {e}", flush=True)
    return result


async def _attach_variant_images(shop, access_token, product_id, product_media, product_variants, per_variant_options, gallery_urls=None):
    print(f"🖼️  Attaching per-variant images...", flush=True)

    def _extract_image_id(url: str) -> str:
        if not url or not isinstance(url, str):
            return ""
        base = url.split("?")[0].split("#")[0]
        base = base.rsplit("/", 1)[-1]
        match = re.match(r"([A-Za-z0-9]+)", base)
        return match.group(1) if match else ""

    id_to_media = {}
    for m in product_media or []:
        try:
            shopify_url = (m.get('image') or {}).get('url') or ""
            mid = m.get('id')
            if shopify_url and mid:
                fname_id = _extract_image_id(shopify_url)
                if fname_id:
                    id_to_media[fname_id] = mid
                    print(f"      📁 Media: id={fname_id} → mediaId=...{mid[-8:]}", flush=True)
        except Exception:
            pass

    print(f"   • Indexed {len(id_to_media)} media items", flush=True)

    sku_to_variant_id = {}
    for v in product_variants or []:
        if v.get('sku') and v.get('id'):
            sku_to_variant_id[v['sku']] = v['id']

    print(f"   • Indexed {len(sku_to_variant_id)} variants", flush=True)

    updates = []
    for entry in per_variant_options or []:
        asin = entry.get("asin")
        v_img = entry.get("image")
        variant_id = sku_to_variant_id.get(asin)
        if not variant_id or not v_img:
            continue
        fname_id = _extract_image_id(v_img)
        print(f"      🔍 Variant {asin}: fname_id={fname_id}", flush=True)
        media_id = id_to_media.get(fname_id)
        if not media_id and gallery_urls and v_img in gallery_urls:
            pos = gallery_urls.index(v_img)
            position_ids = [m.get('id') for m in (product_media or []) if m.get('id')]
            if pos < len(position_ids):
                media_id = position_ids[pos]
                print(f"      ✅ Position fallback: {asin} → media[{pos}]", flush=True)
        if not media_id:
            print(f"   ⚠️  No match for {asin}", flush=True)
            continue
        updates.append({"id": variant_id, "mediaId": media_id})

    if not updates:
        print(f"   ⚠️  No updates", flush=True)
        return

    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id }
        userErrors { field message }
      }
    }
    """
    res = await shopify_graphql(shop, access_token, mutation, {"productId": product_id, "variants": updates})
    if 'errors' in res:
        print(f"❌ errors: {res['errors']}", flush=True)
        return
    ue = res.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors', [])
    if ue:
        print(f"❌ userErrors: {ue}", flush=True)
        return
    print(f"   ✅ Attached images to {len(updates)} variants", flush=True)


async def create_shopify_product_with_variants(shop, access_token, product_data, variants_raw, markup_val, markup_type, extra_percent, tax_rate) -> dict:
    print(f'🛠️  create_shopify_product_with_variants: {len(variants_raw)} variants', flush=True)

    location_id = "gid://shopify/Location/104777056292"

    per_variant_options = []
    for idx, v_raw in enumerate(variants_raw):
        opt_values = {}
        clean_ov = v_raw.get("option_values") or []
        if clean_ov:
            for ov in clean_ov:
                name = (ov or {}).get("name")
                value = (ov or {}).get("value")
                if name and value:
                    opt_values[str(name)] = str(value).strip()
        else:
            for attr in v_raw.get("variant_attributes") or []:
                if attr.get("name") and attr.get("value"):
                    opt_values[str(attr["name"])] = str(attr["value"]).strip()

        per_variant_options.append({
            "index": idx,
            "asin": v_raw.get("asin") or f"variant-{idx}",
            "opts": opt_values,
            "image": v_raw.get("image"),
        })

    option_names = []
    for entry in per_variant_options:
        for name in entry["opts"].keys():
            if name not in option_names:
                option_names.append(name)

    if not option_names:
        option_names = ["Title"]
        for entry in per_variant_options:
            entry["opts"]["Title"] = entry["asin"]

    for entry in per_variant_options:
        asin_suffix = entry["asin"][-6:]
        for name in option_names:
            if not entry["opts"].get(name):
                entry["opts"][name] = f"Variant-{asin_suffix}"

    product_options = []
    for name in option_names:
        values = []
        seen = set()
        for entry in per_variant_options:
            val = entry["opts"][name]
            if val not in seen:
                seen.add(val)
                values.append({"name": val})
        product_options.append({"name": name, "values": values})

    gallery_urls = []
    gallery_seen = set()

    def _register(url):
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        if url not in gallery_seen:
            gallery_seen.add(url)
            gallery_urls.append(url)

    for img in product_data.get('images') or []:
        _register(img)
    for entry in per_variant_options:
        _register(entry.get("image"))

    print(f"   📸 Registered {len(gallery_urls)} unique URLs", flush=True)

    inventory_quantities = [{'locationId': location_id, 'name': 'available', 'quantity': 100}] if location_id else []

    shopify_variants = []
    for idx, v_raw in enumerate(variants_raw):
        entry = per_variant_options[idx]
        price_val = v_raw.get("price", 0.0)
        if isinstance(price_val, (int, float)):
            price = float(price_val)
        elif isinstance(price_val, dict):
            price = float(price_val.get("amount", 0.0))
        else:
            try:
                price = float(price_val)
            except (TypeError, ValueError):
                price = 0.0

        if markup_type == "percent":
            base_price = price + (price * (markup_val / 100.0))
        elif markup_type == "both":
            base_price = (price + markup_val) * (1 + extra_percent / 100.0)
        else:
            base_price = price + markup_val
        v_final_price = round(base_price + (base_price * (tax_rate / 100.0)), 2)

        option_values_payload = []
        for opt_name in option_names:
            option_values_payload.append({"name": entry["opts"][opt_name], "optionName": opt_name})

        shopify_variants.append({
            "price": str(v_final_price),
            "sku": v_raw.get("asin", ""),
            "inventoryItem": {"tracked": True, "measurement": {"weight": {"value": 0.5, "unit": "KILOGRAMS"}}},
            "inventoryQuantities": inventory_quantities,
            "optionValues": option_values_payload,
        })

    mutation = """
    mutation productSet($input: ProductSetInput!) {
      productSet(input: $input) {
        product {
          id
          media(first: 100) {
            nodes {
              id
              ... on MediaImage { image { url } }
            }
          }
          variants(first: 100) {
            nodes { id sku }
          }
        }
        userErrors { field message }
      }
    }
    """

    amazon_categories = product_data.get('categories', []) or []
    prod_type = product_data.get('product_type') or (amazon_categories[-1] if amazon_categories else "General")
    raw_details = product_data.get("details", {})
    enhanced_description = _build_description_with_metafields(product_data.get("description", ""), raw_details)

    input_data = {
        'title': (product_data.get('title') or 'Untitled')[:255],
        'descriptionHtml': enhanced_description,
        'vendor': product_data.get('brand', '') or '',
        'productType': prod_type,
        'tags': product_data.get('tags', []) or [],
        'status': 'ACTIVE',
        'productOptions': product_options,
        'variants': shopify_variants,
    }
    if gallery_urls:
        input_data['files'] = [{'originalSource': u} for u in gallery_urls]
    if amazon_categories:
        cat_id = await get_shopify_category_id(shop, access_token, amazon_categories)
        if cat_id:
            input_data['category'] = cat_id

    print(f'   Sending productSet ({len(shopify_variants)} variants, {len(gallery_urls)} files)', flush=True)
    result = await shopify_graphql(shop, access_token, mutation, {'input': input_data})

    if 'errors' in result:
        return result
    user_errors = result.get('data', {}).get('productSet', {}).get('userErrors', [])
    if user_errors:
        return {'errors': user_errors}

    product_obj = result.get('data', {}).get('productSet', {}).get('product') or {}
    product_id = product_obj.get('id')
    print(f'✅ productSet succeeded', flush=True)

    if product_id:
        media_nodes = (product_obj.get('media') or {}).get('nodes') or []
        variant_nodes = (product_obj.get('variants') or {}).get('nodes') or []
        await _attach_variant_images(shop, access_token, product_id, media_nodes, variant_nodes, per_variant_options, gallery_urls)
        try:
            await publish_product(shop, access_token, product_id)
        except Exception as e:
            print(f"Auto-publish failed: {e}", flush=True)
    return result


def _apply_markup(base_price, markup_val, markup_type, extra_percent, tax_rate):
    if base_price is None:
        return 0.0
    markup_val = float(markup_val or 0.0)
    extra_percent = float(extra_percent or 0.0)
    tax_rate = float(tax_rate or 0.0)
    if markup_type == "percent":
        base = base_price + (base_price * (markup_val / 100.0))
    elif markup_type == "both":
        base = (base_price + markup_val) * (1 + extra_percent / 100.0)
    else:
        base = base_price + markup_val
    return round(base + (base * (tax_rate / 100.0)), 2)


async def set_product_metafields_smart(shop, access_token, product_id, raw_details):
    if not raw_details or not product_id:
        return {"success": True, "skipped": True}
    metafields = []
    weight_str = raw_details.get("item_weight") or raw_details.get("package_weight")
    if weight_str:
        num_match = re.search(r'[\\d.]+', str(weight_str).lower())
        if num_match:
            num = float(num_match.group())
            unit = "KILOGRAMS"
            if "pound" in str(weight_str).lower() or "lb" in str(weight_str).lower():
                unit = "POUNDS"
            metafields.append({"namespace": "shipping", "key": "weight", "type": "weight", "value": '{"value": ' + str(num) + ', "unit": "' + unit + '"}'})
    if raw_details.get("asin"):
        metafields.append({"namespace": "custom", "key": "asin", "type": "single_line_text_field", "value": str(raw_details["asin"])})
    if not metafields:
        return {"success": True, "count": 0}
    mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { key namespace }
        userErrors { field message }
      }
    }
    """
    payload = [{**m, "ownerId": product_id} for m in metafields]
    result = await shopify_graphql(shop, access_token, mutation, {"metafields": payload})
    return result


async def add_variant_to_existing_product(shop, access_token, product_id, variant_data, all_options, **kwargs):
    return {'errors': [{'message': 'Not implemented'}]}

async def get_shopify_product_by_sku(shop, access_token, sku):
    return None

async def update_shopify_product_status(shop, access_token, shopify_product_id, is_available):
    return True

async def set_inventory_quantity(shop, access_token, inventory_item_id, quantity):
    return True

async def sync_update_shopify_price(shop_domain, access_token, shopify_product_id, new_price, refresh_token=None, compare_at_price=None):
    return True

async def set_product_metafields(shop, access_token, product_id, metafields):
    return True
'''

def main():
    target = "app/services/shopify.py"
    if not os.path.exists("app"):
        print(f"❌ ERROR: 'app' folder not found. Run from project root.")
        return
    print(f"Writing to {target}...")
    with open(target, "w", encoding="utf-8") as f:
        f.write(NEW_CODE)
    print("✅ File updated!")
    print("\nVerify:")
    print("  python -c \"import inspect; from app.services import shopify; print('HAS _attach:', hasattr(shopify, '_attach_variant_images'))\"")

if __name__ == "__main__":
    main()