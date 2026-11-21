# app/worker/stock_utils.py
import re
from typing import Optional

def _get_availability(v_raw: dict):
    val = v_raw.get("is_available")
    if val is None:
        val = v_raw.get("in_stock")
    return val


def _resolve_stock(available, stock_qty, default_stock_qty: int = 0) -> int | None:
    if available is None:
        return None
    if not available:
        return 0
    if stock_qty is None:
        return int(default_stock_qty)
    try:
        return int(stock_qty)
    except (TypeError, ValueError):
        return int(default_stock_qty)


def _extract_stock(raw_product: dict, raw_html: str = None):
    """
    Amazon HTML se stock extract karta hai.
    Add to Cart button visible -> True, 100
    Hidden ya Other Sellers -> False, 0
    """
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # 1. Check for "Other Sellers"
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0
    print("✅ [DEBUG] 'Other sellers' check pass", flush=True)

    # 2. Strict Add to Cart Button Check
    # Hum "add-to-cart-button" ya "submit.add-to-cart" wale button ko dhundh rahe hain
    button_pattern = r'<(?:input|span)[^>]*id=["\'](?:add-to-cart-button|submit\.add-to-cart)["\'][^>]*>'
    
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("⚠️ [DEBUG] Koi bhi 'add-to-cart-button' match nahi mila.", flush=True)
        return False, 0

    print(f"✅ [DEBUG] Total {len(matches)} button(s) match mile.", flush=True)
    
    is_visible = False
    
    for match in matches:
        start_idx = max(0, match.start() - 500)
        context = html_lower[start_idx:match.start()]
        
        # Skip hidden or nav-assist buttons
        if 'nav-assist' in context or 'display: none' in context or 'aok-hidden' in context:
            print("⚠️ [DEBUG] Ek hidden/nav-assist button mila, skip kar rahe hain...", flush=True)
            continue 
        
        button_tag = match.group(0).lower()
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag:
            print("⚠️ [DEBUG] Button tag mein hi display:none hai, skip...", flush=True)
            continue

        # Visible button found
        is_visible = True
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        break

    if is_visible:
        return True, 100

    # 3. Fallback Check
    if 'primary-availability-message' in html_lower:
        if 'out of stock' in html_lower or 'currently unavailable' in html_lower:
             print("❌ [DEBUG] Out of Stock text mila -> False, 0", flush=True)
             return False, 0

    print("❌ [DEBUG] Koi bhi visible button nahi mila (out of stock) -> False, 0", flush=True)
    return False, 0