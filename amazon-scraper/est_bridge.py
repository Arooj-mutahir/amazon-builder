import asyncio
from app.services.amazon_bridge import get_shopify_product_data

async def test():
    asin = "B0BGN1YDJH" # Aapka test ASIN
    print(f"Fetching data for {asin}...\n")
    
    data = await get_shopify_product_data(asin)
    
    print(f"Parent price: {data.get('price')}")
    print(f"Parent stock: {data.get('stock_qty')}, in_stock: {data.get('is_available')}")
    print("-" * 50)
    
    variants = data.get('variant_products', [])
    print(f"Total Variants Found: {len(variants)}\n")
    
    for v in variants:
        print(f"{v.get('asin')}: price={v.get('price')}, in_stock={v.get('in_stock')}, stock_qty={v.get('stock_qty')}")

if __name__ == "__main__":
    asyncio.run(test())