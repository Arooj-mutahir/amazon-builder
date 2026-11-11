import asyncio
from app.services.amazon_bridge import get_shopify_product_data

async def main():
    asins = [
        ("B09ZY7WY8P", "Recharge"),
        ("B0BWDB4PJD", "Light Up Mask"),
        ("B0D3HNQT6V", "Voice Recognition Mask"),
        ("B0C2PZTS65", "Upgrades Led Mask"),
    ]
    for asin, label in asins:
        print(f"\n{'=' * 60}")
        print(f"Fetching {asin} ({label})...")
        try:
            data = await get_shopify_product_data(asin)
            imgs = data.get("images") or []
            print(f"  Title: {str(data.get('title'))[:60]}")
            print(f"  Images count: {len(imgs)}")
            print(f"  First image: {imgs[0] if imgs else None}")
            vps = data.get("variant_products") or []
            print(f"  Variant products: {len(vps)}")
            for vp in vps[:3]:
                v_img = (vp.get("images") or [None])[0]
                print(f"    child ASIN={vp.get('asin')} img={str(v_img)[:70]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        await asyncio.sleep(2)

asyncio.run(main())