import httpx
import asyncio
import logging
from app.worker.stock_utils import _extract_stock

logger = logging.getLogger(__name__)

async def get_shopify_product_data(asin: str) -> dict:
    """
    OmkarCloud server se data layega aur Shopify ke mukammal format mein return karega.
    """
    url = f"http://localhost:8000/products/details?product={asin}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not data or "asin" not in data:
                raise Exception(f"OmkarCloud se sahi data nahi mila: {asin}")

            # 1. Images Extract Karein
            images_list = []
            if data.get("images"):
                for img in data["images"]:
                    if img.get("link"):
                        images_list.append(img["link"])

            # 2. Variations (Shopify ke liye behtar format)
            variant_attributes = []
            variant_products = []
            
            if data.get("variations"):
                variations_data = data["variations"]
                
                if variations_data.get("dimensions"):
                    for dim in variations_data["dimensions"]:
                        for val in dim.get("values", []):
                            variant_attributes.append({
                                "name": dim.get("name"),
                                "value": val
                            })
                
                if variations_data.get("products"):
                    for prod in variations_data["products"]:
                        variant_products.append({
                            "asin": prod.get("asin"),
                            "attributes": prod.get("attributes"),
                            "price": prod.get("price", {}).get("amount") if isinstance(prod.get("price"), dict) else prod.get("price"),
                            "is_current": prod.get("is_current", False)
                        })

            # 3. Categories
            categories = []
            if data.get("categories"):
                categories = [cat["name"] for cat in data["categories"] if cat.get("name")]

            # 4. Price & List Price
            price = 0.0
            list_price = None
            if data.get("price"):
                price = float(data["price"].get("amount", 0))
                if data["price"].get("list_price"):
                    list_price = float(data["price"]["list_price"].get("amount", 0))

            # 5. Brand Name
            brand_name = ""
            if data.get("brand"):
                if isinstance(data["brand"], dict):
                    brand_name = data["brand"].get("name", "")
                else:
                    brand_name = str(data["brand"])

            # 6. Details / Specifications
            details = data.get("details", {})
            item_weight = details.get("item_weight") or details.get("package_dimensions", "").split(";")[-1].strip()
            item_dimensions = details.get("product_dimensions") or details.get("package_dimensions", "").split(";")[0].strip()

            # 7. Bullets Extract Karein
            bullets = data.get("bullets", [])

            # 8. Bullets to HTML
            bullets_html = ""
            if bullets:
                bullets_html = "<ul>\n"
                for bullet in bullets:
                    bullets_html += f"  <li>{bullet}</li>\n"
                bullets_html += "</ul>"

            # 9. Rating & Reviews
            rating = data.get("rating", {})
            rating_avg = rating.get("average", 0.0) if isinstance(rating, dict) else 0.0
            reviews_count = rating.get("count", 0) if isinstance(rating, dict) else 0

            # ==========================================
            # 🔥 10. STOCK CHECK (Naya Code)
            # ==========================================
            raw_html = None
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Referer": "https://www.google.com/"
                    }
                    amazon_url = f"https://www.amazon.com/dp/{asin}"
                    resp = await client.get(amazon_url, headers=headers, follow_redirects=True)
                    raw_html = resp.text
            except Exception as e:
                logger.error(f"HTML fetch error for stock: {e}")

            # Stock check karo
            is_available, stock_qty = _extract_stock({}, raw_html)
            
            if is_available:
                final_stock = 100
                final_available = True
            else:
                final_stock = 0
                final_available = False

            print(f"📦 [BRIDGE STOCK] ASIN={asin}, Available={final_available}, Stock={final_stock}", flush=True)

            # 11. Shopify Format Return Karein
            return {
                "title": data.get("title"),
                "description": bullets_html,
                "brand": brand_name,
                "images": images_list,
                "price": price,
                "list_price": list_price,
                "stock_quantity": final_stock,        # 🔥 FIXED
                "is_available": final_available,      # 🔥 FIXED
                "asin": data.get("asin"),
                "parent_asin": data.get("variations", {}).get("parent_asin"),
                "variant_attributes": variant_attributes,
                "variant_products": variant_products,
                "tags": categories,
                "product_type": categories[-1] if categories else "General",
                "feature_bullets": bullets,
                "specifications": details,
                "item_weight": item_weight,
                "item_dimensions": item_dimensions,
                "rating": rating_avg,
                "reviews_count": reviews_count
            }

    except Exception as e:
        logger.error(f"Bridge Error: {e}")
        raise Exception(f"Scraper Data Error: {str(e)}")