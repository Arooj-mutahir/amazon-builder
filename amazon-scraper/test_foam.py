import re
from amazon import fetch, parsers, sites

ASIN = "B08HDJC2JF"

print("Fetching page...")
h = fetch.page("US", f"/dp/{ASIN}")

print("\n=== COLOR IMAGES & ASIN ===")
print("Has colorImages:", '"colorImages"' in h)

# Extract colorToAsin safely
m = re.search(r'"colorToAsin"\s*:\s*(\{[^{}]+\})', h)
if m:
    print("colorToAsin:", m.group(1))
else:
    print("colorToAsin: NONE")

# Extract colorImages keys
m2 = re.search(r'"colorImages"\s*:\s*\{', h)
if m2:
    start = m2.end() - 1
    depth = 0
    end = start
    for i in range(start, len(h)):
        if h[i] == '{': depth += 1
        elif h[i] == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    snippet = h[start:end]
    keys = re.findall(r'"([^"]+)"\s*:\s*\[', snippet)
    print("colorImages keys:", keys[:10])

print("\n=== PARSED IMAGES (variant + asin) ===")
d = parsers.product_page(h, sites.site("US"))
for i, img in enumerate(d.get("images") or []):
    print(f"  [{i}] variant={img.get('variant')!r:25} asin={img.get('asin')!r}")

print("\n=== VARIATION PRODUCTS ===")
for vp in d.get("variations", {}).get("products", []):
    print(f"  ASIN={vp.get('asin')} attrs={vp.get('attributes')}")