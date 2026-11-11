from amazon import fetch, parsers, sites

site = sites.site("US")
html = fetch.page("US", "/dp/B0BWDB4PJD")
data = parsers.product_page(html, site)

print(f"=== IMAGES ===")
for i, img in enumerate(data.get('images') or []):
    print(f"  [{i}] variant={img.get('variant')!r} asin={img.get('asin')!r}")
    print(f"       link={str(img.get('link'))[:70]}")

print(f"\n=== VARIANT PRODUCTS ===")
for vp in data.get('variations', {}).get('products', []):
    print(f"  ASIN={vp.get('asin')} attrs={vp.get('attributes')}")