import httpx
import asyncio
import logging

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
                
                # A. Dimensions (Options) nikalein
                if variations_data.get("dimensions"):
                    for dim in variations_data["dimensions"]:
                        for val in dim.get("values", []):
                            variant_attributes.append({
                                "name": dim.get("name"),
                                "value": val
                            })
                
                # B. Har specific variation (Product) ki detail nikalein
                if variations_data.get("products"):
                    for prod in variations_data["products"]:
                        variant_products.append({
    "asin": prod.get("asin"),
    "attributes": prod.get("attributes"),
    "price": prod.get("price", {}).get("amount") if isinstance(prod.get("price"), dict) else prod.get("price"), # ✅
    "is_current": prod.get("is_current", False)
})
            # 3. Categories (Tags ke liye)
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

            # 7. Bullets Extract Karein (As a list)
            bullets = data.get("bullets", [])

            # 8. Bullets ko HTML format mein badlein (Description ke liye)
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

            # 10. Shopify Format Return Karein
            return {
                "title": data.get("title"),
                "description": bullets_html, # HTML Format
                "brand": brand_name,
                "images": images_list,
                "price": price,
                "list_price": list_price,
                "stock_quantity": 100,
                "is_available": data.get("availability", {}).get("is_in_stock", True),
                "asin": data.get("asin"),
                "parent_asin": data.get("variations", {}).get("parent_asin"),
                "variant_attributes": variant_attributes, # Options list
                "variant_products": variant_products,     # ✅ NAYA: Har variant ki asin aur detail
                "tags": categories,
                "product_type": categories[-1] if categories else "General",
                "feature_bullets": bullets, # ✅ YAHAN ALAG SE BULLETS MIL RAHE HAIN
                "specifications": details,
                "item_weight": item_weight,
                "item_dimensions": item_dimensions,
                "rating": rating_avg,
                "reviews_count": reviews_count
            }

    except Exception as e:
        logger.error(f"Bridge Error: {e}")
        raise Exception(f"Scraper Data Error: {str(e)}")


# ============================================
# TESTING KE LIYE
# ============================================
if __name__ == "__main__":
    async def test():
        print("Testing OmkarCloud to Shopify Bridge...")
        
        # Test ASIN
        asin = "B00BGVLO1G" 
        
        try:
            product_data = await get_shopify_product_data(asin)
            print("\n✅ Data Successfully Fetched and Formatted!")
            print("-" * 40)
            print(f"Title: {product_data['title']}")
            print(f"Brand: {product_data['brand']}")
            print(f"Price: ${product_data['price']}")
            print(f"Rating: {product_data['rating']} ({product_data['reviews_count']} reviews)")
            print(f"Images: {len(product_data['images'])} found")
            print(f"Tags: {product_data['tags']}")
            print(f"Variations (Options): {len(product_data['variant_attributes'])} found")
            print(f"Variation Products: {len(product_data['variant_products'])} found")
            print(f"Item Weight: {product_data['item_weight']}")
            print(f"Item Dimensions: {product_data['item_dimensions']}")
            print("-" * 40)
            
            print("✅ FEATURE BULLETS (List format):")
            if product_data['feature_bullets']:
                for i, bullet in enumerate(product_data['feature_bullets'], 1):
                    print(f"  {i}. {bullet[:80]}...") # Pehle 80 chars
            else:
                print("  No bullets found.")

            print("-" * 40)
            print("✅ VARIATION PRODUCTS (Specific ASINs):")
            if product_data['variant_products']:
                for vp in product_data['variant_products']:
                    print(f"  ASIN: {vp['asin']} | Attributes: {vp['attributes']} | Current: {vp['is_current']}")
            else:
                print("  No variant products found.")
                
            print("-" * 40)
            print("✅ DESCRIPTION (HTML Format):")
            print(product_data['description'][:300] + "...")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")

    asyncio.run(test())