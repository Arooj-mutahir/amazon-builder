import asyncio
from app.services.amazon_bridge import get_shopify_product_data

async def main():
    asins = [
        ("B0CD8SHNH1", "Purple"),
        ("B0B8T72WYM", "White"),
        ("B0CD8W1FJS", "Jet Black"),
        ("B09JCLNMNK", "Camo"),
        ("B08HDHTHDS", "Red"),
        ("B08HDHNC7Q", "Blue"),
        ("B08HDJC2JF", "Green"),
    ]
    for asin, color in asins:
        try:
            d = await get_shopify_product_data(asin)
            imgs = d.get("images") or []
            print(f"{color:12} ASIN={asin} img={str(imgs[0])[:70] if imgs else 'NONE'}")
        except Exception as e:
            print(f"{color:12} ASIN={asin} ❌ {e}")

asyncio.run(main())