from amazon import fetch, parsers, sites

site = sites.site("US")
html = fetch.page("US", "/dp/B08HDJC2JF")
data = parsers.product_page(html, site)

print(f"Total images: {len(data.get('images') or [])}")
print()

print("=== IMAGES (full detail) ===")
for i, img in enumerate(data.get("images") or []):
    print(f"[{i}]")
    print(f"  variant={img.get('variant')!r}")
    print(f"  asin={img.get('asin')!r}")
    print(f"  link={img.get('link')}")
    print(f"  thumbnail={img.get('thumbnail')}")
    print()