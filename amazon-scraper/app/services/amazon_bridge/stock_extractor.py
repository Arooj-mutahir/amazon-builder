import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0
    print("✅ [DEBUG] 'Other sellers' check pass", flush=True)

    real_button_pattern = r'<span[^>]*\bid=["\']submit\.add-to-cart["\'][^>]*>.*?<input[^>]*\bid=["\']add-to-cart-button["\'][^>]*>'
    
    match = re.search(real_button_pattern, raw_html, re.IGNORECASE | re.DOTALL)
    
    if match:
        print("✅ [DEBUG] Asli button match mil gaya!", flush=True)
        
        start_idx = max(0, match.start() - 1000)
        context = html_lower[start_idx:match.start()]
        
        if 'display: none' in context or 'aok-hidden' in context:
            print("❌ [DEBUG] Parent 'display: none' ya 'aok-hidden' mein hai -> False, 0", flush=True)
            return False, 0
            
        print("✅ [DEBUG] Button visible hai -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] Asli button match NAHI mila (regex fail)", flush=True)

    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("✅ [DEBUG] 'In Stock' text mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0