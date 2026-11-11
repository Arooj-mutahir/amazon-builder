import asyncio
from app.services.amazon_bridge import get_shopify_product_data

async def main():
    data = await get_shopify_product_data("B08HDJC2JF")
    
    print("=== AMAZON_BRIDGE: VARIANT PRODUCTS ===")
    for vp in data.get("variant_products") or []:
        imgs = vp.get("images") or [None]
        print(f"  ASIN={vp.get('asin'):15} img={str(imgs[0])[:80]}")
    print()

asyncio.run(main())