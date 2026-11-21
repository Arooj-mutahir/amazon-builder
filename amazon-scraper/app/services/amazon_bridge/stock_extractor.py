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
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # 1. BOT / CAPTCHA CHECK
    if "javascript is disabled" in html_lower or "not a robot" in html_lower or "validatecaptcha" in html_lower:
        print("❌ [BOT DETECTED] Amazon ne Captcha/Bot page bheja hai. Stock 0 rakha ja raha hai.", flush=True)
        return False, 0

    # 2. OUT OF STOCK CHECK (Text Based)
    if "currently unavailable" in html_lower or "out of stock" in html_lower:
        print("❌ [DEBUG] 'Currently unavailable' ya 'Out of Stock' text mila -> False, 0", flush=True)
        return False, 0

    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0

    # 3. STRICT BUTTON CHECK
    # Sirf 'add-to-cart-button' dhundh rahe hain (purana submit.add-to-cart hata diya)
    button_pattern = r'<input[^>]*id=["\']add-to-cart-button["\'][^>]*>'
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("❌ [DEBUG] Koi bhi 'add-to-cart-button' nahi mila -> False, 0", flush=True)
        return False, 0

    is_visible = False
    for match in matches:
        # Button ke 1000 chars pehle ka context dekho
        start_idx = max(0, match.start() - 1000)
        context = html_lower[start_idx:match.start()]
        
        # Skip hidden or nav-assist buttons
        if 'nav-assist' in context or 'display: none' in context or 'aok-hidden' in context:
            print("⚠️ [DEBUG] Ek hidden/nav-assist button mila, skip kar rahe hain...", flush=True)
            continue
        
        # Button tag khud hidden toh nahi?
        button_tag = match.group(0).lower()
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag or 'aria-hidden="true"' in button_tag:
            print("⚠️ [DEBUG] Button tag mein hi hidden hai, skip...", flush=True)
            continue

        # Agar sab pass ho gaya, matlab button visible hai
        is_visible = True
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        break

    if is_visible:
        return True, 100

    # Fallback: Agar button toh hai par hidden hai
    print("❌ [DEBUG] Button hidden hai (out of stock) -> False, 0", flush=True)
    return False, 0