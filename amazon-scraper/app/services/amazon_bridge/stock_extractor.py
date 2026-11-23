# app/services/amazon_bridge/stock_extractor.py
import re

def extract_stock_from_html(raw_html: str) -> tuple[bool, int]:
    """
    Returns: (is_available: bool, stock_qty: int)
    Logic: Add to Cart button visible -> (True, 100)
           Button hidden/missing/captcha -> (False, 0)
    """
    print("\n🔍 [DEBUG] Stock extraction shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()

    # 1. BOT / CAPTCHA CHECK
    if "javascript is disabled" in html_lower or "not a robot" in html_lower or "validatecaptcha" in html_lower or "captcha" in html_lower:
        print("❌ [BOT DETECTED] Captcha/Bot page mila -> False, 0", flush=True)
        return False, 0

    # 2. OUT OF STOCK TEXT CHECK
    if "currently unavailable" in html_lower or "out of stock" in html_lower:
        print("❌ [DEBUG] 'Currently unavailable' ya 'Out of Stock' text mila -> False, 0", flush=True)
        return False, 0

    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0

    # 3. STRICT BUTTON CHECK
    button_pattern = r'<input[^>]*id=["\']add-to-cart-button["\'][^>]*>'
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("❌ [DEBUG] Koi bhi 'add-to-cart-button' nahi mila -> False, 0", flush=True)
        return False, 0

    is_visible = False
    for match in matches:
        start_idx = max(0, match.start() - 1000)
        context = html_lower[start_idx:match.start()]
        button_tag = match.group(0).lower()
        
        if 'nav-assist' in context or 'display: none' in context or 'aok-hidden' in context:
            continue
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag or 'aria-hidden="true"' in button_tag:
            continue

        is_visible = True
        break

    if is_visible:
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Button hidden hai (out of stock) -> False, 0", flush=True)
    return False, 0