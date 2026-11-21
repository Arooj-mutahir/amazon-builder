import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # 1. Check for "Other Sellers" (Out of Stock signal)
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0
    print("✅ [DEBUG] 'Other sellers' check pass", flush=True)

    # 2. Button ko dhundhein
    button_pattern = r'id=["\']add-to-cart-button["\']'
    match = re.search(button_pattern, html_lower)
    
    if match:
        print("✅ [DEBUG] 'add-to-cart-button' ID HTML mein mil gayi.", flush=True)
        
        # 🔥 FIX: Button ke PEHLE ke 500 characters check karein (parent div ke liye)
        # Amazon button ko ek div ke andar rakhta hai, aur hidden class us div par hoti hai
        start_idx = max(0, match.start() - 500)
        context_before = html_lower[start_idx:match.start()]
        
        # Agar button ke PEHLE 'display: none' ya 'aok-hidden' hai, toh button hidden hai
        if 'display: none' in context_before or 'aok-hidden' in context_before or 'a-hidden' in context_before:
            print("❌ [DEBUG] Button hidden hai (parent div mein display:none/aok-hidden mila) -> False, 0", flush=True)
            return False, 0
        
        # Agar button ke BAAD 'See All Buying Options' hai, toh button kaam nahi karega
        end_idx = min(len(html_lower), match.end() + 500)
        context_after = html_lower[match.end():end_idx]
        if 'see all buying options' in context_after:
            print("❌ [DEBUG] Button ke baad 'See All Buying Options' mila -> False, 0", flush=True)
            return False, 0
            
        print("✅ [DEBUG] Button VISIBLE hai -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] 'add-to-cart-button' ID nahi mili.", flush=True)

    # Fallback Check
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("✅ [DEBUG] Fallback: 'In Stock' text mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0