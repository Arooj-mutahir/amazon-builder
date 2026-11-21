import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        return False, 0

    html_lower = raw_html.lower()

    # 1. Agar page pe "Currently Unavailable" ya "Out of Stock" likha hai -> Seedha False
    if 'currently unavailable' in html_lower or 'out of stock' in html_lower:
        print("❌ [DEBUG] 'Currently unavailable' ya 'Out of Stock' text mila -> False, 0", flush=True)
        return False, 0

    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0

    # 2. Ab asli button dhundho (jisme humne pehle wala "nav-assist" filter lagaya tha)
    button_pattern = r'<(?:input|span)[^>]*id=["\'](?:add-to-cart-button|submit\.add-to-cart)["\'][^>]*>'
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("❌ [DEBUG] Button tag hi nahi mila -> False, 0", flush=True)
        return False, 0

    is_visible = False
    for match in matches:
        # Button ke aage ka HTML (500 chars) uthao
        start_idx = max(0, match.start() - 500)
        context = html_lower[start_idx:match.start()]
        
        # Hidden buttons skip karo
        if 'nav-assist' in context or 'display: none' in context or 'aok-hidden' in context:
            continue 
        
        button_tag = match.group(0).lower()
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag or 'aria-hidden="true"' in button_tag:
            continue

        # Agar yahan tak pahunche, matlab button asli aur visible hai
        is_visible = True
        break

    if is_visible:
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        return True, 100

    # 3. Fallback: Agar button toh mila par hidden tha, aur upar out-of-stock text bhi nahi tha
    # Toh check karo ki kahin "In Stock" toh nahi likha
    if 'in stock' in html_lower and 'primary-availability-message' in html_lower:
        print("✅ [DEBUG] 'In Stock' message mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi confirm nahi hua (default out of stock) -> False, 0", flush=True)
    return False, 0