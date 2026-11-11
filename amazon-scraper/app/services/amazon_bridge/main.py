# app/services/amazon_bridge/main.py

import asyncio
import logging
from amazon import fetch, parsers, sites

from .helpers import _img_url, _norm, _brand_name, _price_amount, _rating_avg, _rating_count
from .stock_extractor import _extract_stock
from .description import _extract_clean_description
from .specifications import _extract_specifications
from .size_chart import _extract_size_chart
from .reviews import extract_top_reviews
from .images import extract_all_gallery_images, extract_color_images_map

logger = logging.getLogger(__name__)
DEFAULT_STOCK_QTY = 100

async def get_shopify_product_data(asin: str, default_stock_qty: int = DEFAULT_STOCK_QTY, fetch_all_variants: bool = True) -> dict:
    try:
        site = sites.site("US")

        def _fetch_main():
            h = fetch.page(
                "US", f"/dp/{asin}", {"th": "1", "psc": "1"},
                referer=f"https://www.amazon.com/s?k={asin}",
            )
            if 'data-hook="review"' not in h and 'customer_review-' not in h:
                if parsers.review_treatment(h) == "T1":
                    fetch.drop_session("US", "page")
                    try:
                        retry_h = fetch.page(
                            "US", f"/dp/{asin}", {"th": "1", "psc": "1"},
                            referer=f"https://www.amazon.com/s?k={asin}",
                        )
                        if 'data-hook="review"' in retry_h or 'customer_review-' in retry_h:
                            return retry_h
                    except Exception:
                        pass
            return h

        try:
            html = await asyncio.wait_for(
                asyncio.to_thread(_fetch_main),
                timeout=45.0,
            )
        except asyncio.TimeoutError:
            raise Exception("Amazon main page load timeout (Captcha ya heavy page)")

        raw_data = parsers.product_page(html, site)

        if not raw_data or not raw_data.get("asin"):
            raise Exception(f"Scraper se sahi data nahi mila: {asin}")

        # ========================================================
        # ✅ IMAGES & VARIANTS LOGIC
        # ========================================================
        all_image_urls = [u for u in (_img_url(i) for i in raw_data.get("images") or []) if u]
        for u in extract_all_gallery_images(html):
            if u not in all_image_urls:
                all_image_urls.append(u)
        images_list = list(dict.fromkeys(all_image_urls))
        main_image = images_list[0] if images_list else None

        parent_color_images = extract_color_images_map(html)

        asin_image_map = {}
        variant_image_map = {}
        for img in raw_data.get("images") or []:
            img_url = _img_url(img)
            if not img_url:
                continue
            if img.get("asin"):
                asin_image_map[str(img.get("asin")).strip()] = img_url
            if img.get("variant") and _norm(img.get("variant")) not in ("", "main"):
                variant_image_map[_norm(img.get("variant"))] = img_url

        variations_data = raw_data.get("variations") or {}
        variant_attributes, seen_attr = [], set()
        for dim in variations_data.get("dimensions") or []:
            for val in dim.get("values") or []:
                key = (_norm(dim.get("name")), _norm(val))
                if key not in seen_attr:
                    seen_attr.add(key)
                    variant_attributes.append({"name": dim.get("name"), "value": val})

        parent_price = _price_amount(raw_data.get("price"))
        parent_in_stock, parent_stock_qty = _extract_stock({}, html)

        variant_products = []

        for prod in variations_data.get("products") or []:
            attrs = prod.get("attributes") or {}
            child_asin = prod.get("asin")

            child_price = _price_amount(prod.get("price"))

            # ✅ FAST MODE: Agar fetch_all_variants False hai
            if not fetch_all_variants and parent_in_stock:
                option_values = [{"name": str(k), "value": str(v)} for k, v in attrs.items() if v]
                variant_products.append({
                    "asin": child_asin,
                    "attributes": attrs,
                    "option_values": option_values,
                    "images": [],
                    "price": child_price or parent_price,
                    "in_stock": True,
                    "stock_qty": parent_stock_qty,
                })
                continue

            variant_in_stock, variant_stock_qty = None, None
            child_images = []

            asin_thumb = asin_image_map.get(child_asin) if child_asin else None

            if not asin_thumb:
                for _, attr_val in attrs.items():
                    val_str = _norm(attr_val)
                    if val_str in variant_image_map:
                        asin_thumb = variant_image_map[val_str]
                        break
                    if "&" in val_str:
                        for tok in val_str.split("&"):
                            if tok.strip() in variant_image_map:
                                asin_thumb = variant_image_map[tok.strip()]
                                break
                        if asin_thumb:
                            break

            if child_asin:
                try:
                    await asyncio.sleep(1.5)
                    child_html = await asyncio.wait_for(
                        asyncio.to_thread(fetch.page, "US", f"/dp/{child_asin}"),
                        timeout=20.0,
                    )
                    child_raw = parsers.product_page(child_html, site)

                    fetched = _price_amount(child_raw.get("price"))
                    if fetched > 0:
                        child_price = fetched
                    elif child_price == 0.0:
                        child_price = parent_price

                    variant_in_stock, variant_stock_qty = _extract_stock({}, child_html)

                    for url in extract_all_gallery_images(child_html):
                        if url and url not in child_images:
                            child_images.append(url)

                    for img in child_raw.get("images") or []:
                        url = _img_url(img)
                        if url and url not in child_images:
                            child_images.append(url)

                    print(f"   📦 Variant ASIN {child_asin}: Live Amazon Price=${child_price:.2f} | Stock={variant_stock_qty} (in_stock={variant_in_stock})", flush=True)

                except Exception as e:
                    print(f"   ⚠️ Variant fetch error for {child_asin}: {e}", flush=True)
                    logger.warning(f"Variant fetch failed {child_asin}: {e}")
                    variant_in_stock, variant_stock_qty = False, 0
                    if child_price == 0.0:
                        child_price = parent_price

            if not child_images:
                for _, attr_val in attrs.items():
                    val_str = _norm(attr_val)
                    if val_str in parent_color_images:
                        for u in parent_color_images[val_str]:
                            if u not in child_images:
                                child_images.append(u)
                        if child_images:
                            break

            if asin_thumb:
                if asin_thumb in child_images:
                    child_images.remove(asin_thumb)
                child_images.insert(0, asin_thumb)

            elif not child_images:
                if main_image:
                    child_images = [main_image]

            option_values = [{"name": str(k), "value": str(v)} for k, v in attrs.items() if v]

            variant_products.append({
                "asin": child_asin,
                "attributes": attrs,
                "option_values": option_values,
                "images": child_images,
                "price": child_price,
                "in_stock": variant_in_stock,
                "stock_qty": variant_stock_qty,
            })

        # ========================================================
        # ✅ CATEGORIES & TAGS LOGIC
        # ========================================================
        categories = [cat.get("name") for cat in raw_data.get("categories") or [] if cat.get("name")]
        title_lower = str(raw_data.get("title") or "").lower()
        
        if any(w in title_lower for w in ("pet", "dog", "cat", "puppy")):
            categories = ["Pet Supplies", "Dogs"]
        elif any(w in title_lower for w in ("makeup", "beauty", "lipstick")):
            categories = ["Beauty & Personal Care", "Makeup"]

        bullets = raw_data.get("bullets") or []

        clean_desc_html = _extract_clean_description(html)
        specs_data = _extract_specifications(html)
        size_chart_html = _extract_size_chart(html, raw_data.get("images") or [])
        reviews = extract_top_reviews(html, limit=15, fallback_reviews=raw_data.get("top_reviews"))

        return {
            "title": raw_data.get("title"),
            "bullets": bullets,
            "description": clean_desc_html,
            "specifications": specs_data,
            "size_chart": size_chart_html,
            "reviews": reviews,
            "brand": _brand_name(raw_data.get("brand")),
            "images": images_list,
            "price": parent_price,
            "asin": raw_data.get("asin"),
            "parent_asin": variations_data.get("parent_asin"),
            "variant_attributes": variant_attributes,
            "variant_products": variant_products,
            "tags": categories,  # ✅ Tags sahi set ho gaye
            "product_type": categories[-1] if categories else "General",  # ✅ Product Type sahi set ho gaya
            "is_available": parent_in_stock,
            "stock_qty": parent_stock_qty,
            "rating": _rating_avg(raw_data.get("rating")),
            "reviews_count": _rating_count(raw_data.get("rating")),
            "details": raw_data.get("details") or {},
        }

    except Exception as e:
        logger.error(f"Bridge Error: {e}")
        raise Exception(f"Scraper Data Error: {str(e)}")