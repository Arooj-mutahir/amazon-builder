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

    # 2. Button ID dhundhein
    if 'id="add-to-cart-button"' in html_lower or "id='add-to-cart-button'" in html_lower:
        print("✅ [DEBUG] 'add-to-cart-button' ID HTML mein mil gayi.", flush=True)
        
        # 🔥 FIX: Button ke AAS-PAAS ke context ko check karein, na ki 4000 characters pehle ka
        btn_pos = html_lower.find('add-to-cart-button')
        
        # Button ke pehle ke 500 characters ka context (parent div)
        start_idx = max(0, btn_pos - 500)
        context_before = html_lower[start_idx:btn_pos]
        
        # Agar button ke PEHLE 'display: none' ya 'aok-hidden' hai, toh button hidden hai
        if 'display: none' in context_before or 'aok-hidden' in context_before or 'a-hidden' in context_before:
            print("❌ [DEBUG] Button hidden hai (parent div mein display:none/aok-hidden mila) -> False, 0", flush=True)
            return False, 0
        
        # Button ke baad ke 500 characters ka context
        end_idx = min(len(html_lower), btn_pos + 500)
        context_after = html_lower[btn_pos:end_idx]
        
        # Agar button ke baad 'See All Buying Options' hai, toh button visible nahi hai
        if 'see all buying options' in context_after:
            print("❌ [DEBUG] Button ke baad 'See All Buying Options' mila -> False, 0", flush=True)
            return False, 0
            
        # Prime Exclusive Check (screenshot mein yahi dikh raha tha)
        if 'prime exclusive' in context_before or 'join prime' in context_before:
            print("❌ [DEBUG] Prime Exclusive product mila -> False, 0", flush=True)
            return False, 0

        # Agar upar ke saare checks pass ho gaye, toh button visible hai
        print("✅ [DEBUG] Button VISIBLE hai -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] 'add-to-cart-button' ID nahi mili HTML mein.", flush=True)

    # Fallback Check: Agar button nahi mila par "In Stock" text hai
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("✅ [DEBUG] Fallback: 'In Stock' text mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0