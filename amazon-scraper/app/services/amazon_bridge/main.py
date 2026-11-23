# app/services/amazon_bridge/main.py
import asyncio
import logging
from app.services.amazon_bridge.stock_extractor import extract_stock_from_data
from amazon.products import details as amazon_details  

logger = logging.getLogger(__name__)

async def get_shopify_product_data(asin: str, default_stock_qty: int = 0) -> dict:
    try:
        # 🔥 Direct scraper call (Bina HTTP request ke)
        data = await asyncio.to_thread(amazon_details, asin)

        if not data or "asin" not in data:
            raise Exception(f"Custom Scraper se sahi data nahi mila: {asin}")

        # 1. Images
        images_list = []
        if data.get("images"):
            for img in data["images"]:
                if isinstance(img, dict) and img.get("link"):
                    images_list.append(img["link"])
                elif isinstance(img, str):
                    images_list.append(img)

        # 2. Variations
        variant_attributes = []
        variant_products = []
        variations_data = data.get("variations", {})
        
        if variations_data.get("dimensions"):
            for dim in variations_data["dimensions"]:
                for val in dim.get("values", []):
                    variant_attributes.append({"name": dim.get("name"), "value": val})
        
        if variations_data.get("products"):
            for prod in variations_data["products"]:
                variant_products.append({
                    "asin": prod.get("asin"),
                    "attributes": prod.get("attributes"),
                    "price": prod.get("price", {}).get("amount") if isinstance(prod.get("price"), dict) else prod.get("price"),
                    "is_current": prod.get("is_current", False)
                })

        # 3. Categories & Brand
        categories = [cat.get("name") for cat in data.get("categories", []) if cat.get("name")]
        brand_name = data.get("brand", {}).get("name", "") if isinstance(data.get("brand"), dict) else str(data.get("brand", ""))

        # 4. Price (🔥 FIXED)
        price = 0.0
        list_price = None
        if data.get("price"):
            price_data = data["price"]
            if isinstance(price_data, dict):
                price = float(price_data.get("amount", 0) or 0)
                
                list_price_val = price_data.get("list_price")
                if list_price_val is not None:
                    if isinstance(list_price_val, dict):
                        list_price = float(list_price_val.get("amount", 0) or 0)
                    else:
                        list_price = float(list_price_val)
            else:
                price = float(price_data or 0)

        # 5. Rating & Bullets
        rating = data.get("rating", {})
        rating_avg = rating.get("average", 0.0) if isinstance(rating, dict) else 0.0
        reviews_count = rating.get("count", 0) if isinstance(rating, dict) else 0
        
        bullets = data.get("bullets", [])
        bullets_html = ""
        if bullets:
            bullets_html = "<ul>\n"
            for bullet in bullets:
                bullets_html += f"  <li>{bullet}</li>\n"
            bullets_html += "</ul>"

        # 6. Details / Specifications
        details = data.get("details", {})
        item_weight = details.get("item_weight") or details.get("package_dimensions", "").split(";")[-1].strip()
        item_dimensions = details.get("product_dimensions") or details.get("package_dimensions", "").split(";")[0].strip()

        # ==========================================
        # 🔥 7. STOCK CHECK — parsers.py ka parsed data use karo (no re-parsing)
        # parsers.py ki product_page() already is_add_to_cart_visible,
        # availability, aur buybox compute kar chuka hai.
        # ==========================================
        is_available, stock_qty = extract_stock_from_data(data)

        if is_available:
            final_stock = stock_qty if stock_qty and stock_qty > 0 else 100
            final_available = True
        else:
            final_stock = 0
            final_available = False

        print(f"📦 [BRIDGE STOCK] ASIN={asin}, Available={final_available}, Stock={final_stock}", flush=True)

        # 8. Return Data
        return {
            "title": data.get("title"),
            "description": bullets_html,
            "brand": brand_name,
            "images": images_list,
            "price": price,
            "list_price": list_price,
            "stock_quantity": final_stock,
            "is_available": final_available,
            "is_add_to_cart_visible": final_available,
            "asin": data.get("asin"),
            "parent_asin": variations_data.get("parent_asin"),
            "variant_attributes": variant_attributes,
            "variant_products": variant_products,
            "tags": categories,
            "product_type": categories[-1] if categories else "General",
            "feature_bullets": bullets,
            "specifications": details,
            "item_weight": item_weight,
            "item_dimensions": item_dimensions,
            "rating": rating_avg,
            "reviews_count": reviews_count,
            "top_reviews": data.get("top_reviews", []),
        }

    except Exception as e:
        logger.error(f"Bridge Error: {e}")
        raise Exception(f"Scraper Data Error: {str(e)}")