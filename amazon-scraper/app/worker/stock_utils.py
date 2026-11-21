# app/worker/stock_utils.py
import re

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
    Strict Logic:
    1. Agar "Currently Unavailable" ya "Out of Stock" hai -> False, 0
    2. Agar 'submit.add-to-cart' ya 'add-to-cart-button' visible hai -> True, 100
    3. Agar button hidden hai -> False, 0
    """
    if not raw_html:
        return False, 0

    html_lower = raw_html.lower()

    # 1. Direct Text Check for Out of Stock
    if 'currently unavailable' in html_lower or 'out of stock' in html_lower:
        print("❌ [DEBUG] 'Currently unavailable' ya 'Out of Stock' text mila -> False, 0", flush=True)
        return False, 0

    if 'see all buying options' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0

    # 2. Button Check (Strict)
    # Hum dono ids check kar rahe hain: submit.add-to-cart aur add-to-cart-button
    # Aur humne ensure kiya hai ki button ke aas-paas 'nav-assist' ya 'display: none' na ho
    button_pattern = r'<(?:input|span)[^>]*id=["\'](?:add-to-cart-button|submit\.add-to-cart)["\'][^>]*>'
    
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("❌ [DEBUG] Koi bhi button tag nahi mila -> False, 0", flush=True)
        return False, 0

    # 3. Check Visibility for each match
    for match in matches:
        # 500 characters pehle ka context dekho
        start_idx = max(0, match.start() - 500)
        context = html_lower[start_idx:match.start()]
        
        # Skip hidden or nav-assist buttons
        if 'nav-assist' in context or 'display: none' in context or 'aok-hidden' in context:
            continue
        
        # Check the button tag itself
        button_tag = match.group(0).lower()
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag or 'aria-hidden="true"' in button_tag:
            continue

        # Agar yahan tak aaye, toh button visible hai
        print("✅ [DEBUG] Asli visible button mil gaya -> True, 100", flush=True)
        return True, 100

    # 4. Fallback: Agar button toh hai par hidden hai, aur koi "In Stock" text nahi hai
    print("❌ [DEBUG] Button hidden hai (stock out) -> False, 0", flush=True)
    return False, 0