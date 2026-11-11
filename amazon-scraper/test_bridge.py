# test_bridge.py
import asyncio
from amazon import fetch, parsers, sites

async def main():
    site = sites.site("US")
    html = fetch.page("US", "/dp/B0BWDB4PJD")
    print(f"HTML length: {len(html)}")
    print(f"Has productTitle: {'productTitle' in html}")
    print(f"Has colorImages: {'colorImages' in html}")
    print(f"Has colorToAsin: {'colorToAsin' in html}")
    
    data = parsers.product_page(html, site)
    print(f"\n=== PARSED DATA ===")
    print(f"ASIN: {data.get('asin')}")
    print(f"Title: {str(data.get('title'))[:60]}")
    print(f"Images count: {len(data.get('images') or [])}")
    print(f"\n=== IMAGES ===")
    for i, img in enumerate(data.get('images') or []):
        print(f"  [{i}] variant={img.get('variant')!r} asin={img.get('asin')!r} link={str(img.get('link'))[:60]}")
    
    variations = data.get('variations') or {}
    print(f"\n=== VARIATIONS ===")
    print(f"Parent ASIN: {variations.get('parent_asin')}")
    print(f"Dimensions: {[d.get('name') for d in (variations.get('dimensions') or [])]}")
    print(f"Products count: {len(variations.get('products') or [])}")
    for p in (variations.get('products') or [])[:8]:
        print(f"  ASIN={p.get('asin')} attrs={p.get('attributes')}")

asyncio.run(main())