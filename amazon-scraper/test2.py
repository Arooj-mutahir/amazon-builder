from amazon import fetch
import re
import json

html = fetch.page('US', '/dp/B0BWDB4PJD')

print("=" * 60)
print("HTML LENGTH:", len(html))
print("=" * 60)

# 1. colorToAsin
m = re.search(r'"colorToAsin"\s*:\s*(\{[^{}]*\})', html)
print("\n1. colorToAsin raw:", m.group(1) if m else "NOT FOUND")

# 2. Try to find it more loosely
idx = html.find('"colorToAsin"')
if idx > 0:
    snippet = html[idx:idx + 500]
    print("\n2. colorToAsin snippet:")
    print(snippet)

# 3. dimensionValuesDisplayData
idx = html.find('"dimensionValuesDisplayData"')
if idx > 0:
    snippet = html[idx:idx + 800]
    print("\n3. dimensionValuesDisplayData snippet:")
    print(snippet)

# 4. variationDisplayLabels
idx = html.find('"variationDisplayLabels"')
if idx > 0:
    snippet = html[idx:idx + 400]
    print("\n4. variationDisplayLabels snippet:")
    print(snippet)

# 5. Check landingImage
m = re.search(r'id="landingImage"[^>]*\sdata-old-hires="([^"]+)"', html)
print("\n5. landingImage data-old-hires:", m.group(1) if m else "NOT FOUND")

# 6. Current ASIN in page
m = re.search(r'"currentAsin"\s*:\s*"([A-Z0-9]{10})"', html)
print("\n6. currentAsin:", m.group(1) if m else "NOT FOUND")

# 7. Parent ASIN
m = re.search(r'"parentAsin"\s*:\s*"([A-Z0-9]{10})"', html)
print("\n7. parentAsin:", m.group(1) if m else "NOT FOUND")