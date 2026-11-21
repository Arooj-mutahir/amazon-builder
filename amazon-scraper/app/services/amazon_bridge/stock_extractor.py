import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        return False, 0

    html_lower = raw_html.lower()

    # 1. Check for "Other Sellers" (Out of Stock signal)
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0

    # 🔥 FIX: Asli button ko dhundhein (jo <input> tag hota hai)
    # Amazon ka asli button aisa hota hai: <input id="add-to-cart-button" ...>
    # Hum regex se check karenge ki kya id="add-to-cart-button" kisi <input> tag ke andar hai
    input_button_pattern = r'<input[^>]*\bid=["\']add-to-cart-button["\'][^>]*>'
    match_input = re.search(input_button_pattern, html_lower)

    if match_input:
        print("✅ [DEBUG] Asli <input> button mil gaya.", flush=True)
        
        # Uske pehle ke 500 characters ka context dekhein
        start_idx = max(0, match_input.start() - 500)
        context_before = html_lower[start_idx:match_input.start()]
        
        if 'display: none' in context_before or 'aok-hidden' in context_before:
            print("❌ [DEBUG] Button hidden hai (display:none) -> False, 0", flush=True)
            return False, 0
            
        # Uske baad ke 500 characters ka context dekhein
        end_idx = min(len(html_lower), match_input.end() + 500)
        context_after = html_lower[match_input.end():end_idx]
        
        if 'see all buying options' in context_after:
            print("❌ [DEBUG] Button ke baad 'See All Buying Options' -> False, 0", flush=True)
            return False, 0
            
        print("✅ [DEBUG] Button VISIBLE hai -> True, 100", flush=True)
        return True, 100

    # Agar <input> nahi mila, toh check karein ki kahin <span> ke andar toh nahi hai
    span_button_pattern = r'<span[^>]*\bid=["\']submit\.add-to-cart["\'][^>]*>'
    match_span = re.search(span_button_pattern, html_lower)

    if match_span:
        print("✅ [DEBUG] Asli <span> button mil gaya.", flush=True)
        # Yahan bhi hidden check karein
        start_idx = max(0, match_span.start() - 500)
        context_before = html_lower[start_idx:match_span.start()]
        if 'display: none' in context_before or 'aok-hidden' in context_before:
            return False, 0
        return True, 100

    # Fallback
    print("⚠️ [DEBUG] Asli button nahi mila. Fallback check kar rahe hain.", flush=True)
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0