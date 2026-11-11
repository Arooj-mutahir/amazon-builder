import asyncio
from app.services.amazon_bridge import get_shopify_product_data

async def main():
    data = await get_shopify_product_data("B0BWDB4PJD")
    
    print("=== VARIANT PRODUCTS (bridge) ===")
    for vp in data.get("variant_products") or []:
        print(f"  ASIN={vp.get('asin')}")
        print(f"    attrs={vp.get('attributes')}")
        print(f"    images={(vp.get('images') or [None])[0]}")
        print()

asyncio.run(main())