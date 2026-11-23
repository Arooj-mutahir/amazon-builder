# app/services/amazon_bridge/stock_extractor.py
import re

def extract_stock_from_html(raw_html: str) -> tuple[bool, int]:
    """
    Returns: (is_available: bool, stock_qty: int)
    Logic: Asli visible Add to Cart button -> (True, 100)
           Button hidden/missing/captcha/buying options -> (False, 0)
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

    # 3. OTHER SELLERS CHECK (Agar sirf buying options hain, toh stock 0)
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower or 'other sellers on amazon' in html_lower:
        print("❌ [DEBUG] 'Buying Options' ya 'Other Sellers' mila (Amazon khud stock nahi bech raha) -> False, 0", flush=True)
        return False, 0

    # 4. STRICT BUTTON CHECK (Sirf asli button)
    # Hum exact input tag dhundh rahe hain jiska id 'add-to-cart-button' ho
    button_pattern = r'<input[^>]*id=["\']add-to-cart-button["\'][^>]*>'
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))
    
    if not matches:
        print("❌ [DEBUG] Koi bhi asli 'add-to-cart-button' nahi mila -> False, 0", flush=True)
        return False, 0

    is_visible = False
    for match in matches:
        # Button ke 1000 chars pehle ka context dekho
        start_idx = max(0, match.start() - 1000)
        context = html_lower[start_idx:match.start()]
        button_tag = match.group(0).lower()
        
        # 🔥 NAV-ASSIST / HIDDEN FILTER (Yeh screen-reader waale buttons ko block karega)
        if 'nav-assist' in button_tag or 'nav-assist' in context:
            continue
        if 'display: none' in context or 'aok-hidden' in context:
            continue
        if 'display: none' in button_tag or 'visibility: hidden' in button_tag or 'aria-hidden="true"' in button_tag:
            continue

        # Agar sab pass ho gaya, matlab button visible hai
        is_visible = True
        break

    if is_visible:
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Button hidden hai ya fake hai -> False, 0", flush=True)
    return False, 0