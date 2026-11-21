import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        return False, 0

    html_lower = raw_html.lower()

    # 1. Other sellers check
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        return False, 0

    # 2. Asli button dhundein (id="add-to-cart-button" wala)
    if 'id="add-to-cart-button"' in html_lower or "id='add-to-cart-button'" in html_lower:
        print("✅ [DEBUG] 'add-to-cart-button' ID mili.", flush=True)
        
        # Asli button ki position dhundein
        btn_pos = html_lower.find('id="add-to-cart-button"')
        if btn_pos == -1:
            btn_pos = html_lower.find("id='add-to-cart-button'")
        
        # 🔥 FIX: Button ke PEHLE ke sirf 500 characters check karein
        start_idx = max(0, btn_pos - 500)
        context_before = html_lower[start_idx:btn_pos]
        
        # Agar button ke pehle display:none hai, toh hidden hai
        if 'display: none' in context_before or 'aok-hidden' in context_before:
            print("❌ [DEBUG] Button hidden hai (display:none) -> False, 0", flush=True)
            return False, 0
            
        # Button ke baad ka context (See All Buying Options check)
        end_idx = min(len(html_lower), btn_pos + 500)
        context_after = html_lower[btn_pos:end_idx]
        if 'see all buying options' in context_after:
            print("❌ [DEBUG] Button ke baad 'See All Buying Options' -> False, 0", flush=True)
            return False, 0

        print("✅ [DEBUG] Button VISIBLE hai -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] Button ID nahi mili.", flush=True)

    # Fallback
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        return True, 100

    return False, 0