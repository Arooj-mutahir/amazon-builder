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

    # 2. Check if "add-to-cart-button" exists
    if 'id="add-to-cart-button"' in html_lower or "id='add-to-cart-button'" in html_lower:
        print("✅ [DEBUG] 'add-to-cart-button' ID HTML mein mil gayi.", flush=True)
        
        btn_pos = html_lower.find('add-to-cart-button')
        
        # 🔥 FIX 1: Context range badhayein (4000 characters pehle tak dekhein)
        context_start = max(0, btn_pos - 4000)
        context = html_lower[context_start:btn_pos]
        
        # 🔥 FIX 2: Check hidden classes
        if 'display: none' in context or 'aok-hidden' in context or 'a-hidden' in context:
            print("❌ [DEBUG] Button 'display: none' ya 'hidden' class mein hai -> False, 0", flush=True)
            return False, 0
            
        # 🔥 FIX 3: Check Prime Exclusive (Screenshot mein yahi dikh raha tha)
        if 'prime exclusive' in context or 'join prime' in context:
            print("❌ [DEBUG] Prime Exclusive product mila -> False, 0", flush=True)
            return False, 0

        # 🔥 FIX 4: Check karein ki button ke baad "Add to Cart" ka text hai ya "See All Buying Options"
        # Agar "See All Buying Options" hai, toh button kaam nahi karega
        post_context = html_lower[btn_pos:btn_pos+2000]
        if 'see all buying options' in post_context:
            print("❌ [DEBUG] Button ke baad 'See All Buying Options' mila -> False, 0", flush=True)
            return False, 0
            
        print("✅ [DEBUG] Button VISIBLE hai (Hidden nahi hai) -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] 'add-to-cart-button' ID nahi mili HTML mein.", flush=True)

    # Fallback Check
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("✅ [DEBUG] Fallback: 'In Stock' text mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0