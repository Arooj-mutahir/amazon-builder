# app/services/amazon_bridge/stock_extractor.py
import re

def extract_stock_from_html(raw_html: str) -> tuple[bool, int]:
    """
    Returns: (is_available: bool, stock_qty: int)
    Strict logic: Sirf VISIBLE asli 'add-to-cart-button' milne par hi stock=100
    """
    print("\n🔍 [DEBUG] Stock extraction shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()

    # 1) BOT / CAPTCHA
    if any(x in html_lower for x in ["validatecaptcha", "not a robot", "javascript is disabled", "api-services-support@amazon.com"]):
        print("❌ [BOT/CAPTCHA] -> False, 0", flush=True)
        return False, 0

    # 2) OUT OF STOCK TEXT
    if "currently unavailable" in html_lower or "out of stock" in html_lower:
        print("❌ [DEBUG] 'Currently unavailable' / 'Out of Stock' -> False, 0", flush=True)
        return False, 0

    # 3) OTHER SELLERS / BUYING OPTIONS (Amazon khud nahi bech raha)
    if ("see all buying options" in html_lower
            or "available at a lower price from other sellers" in html_lower
            or "other sellers on amazon" in html_lower):
        print("❌ [DEBUG] Buying Options / Other Sellers -> False, 0", flush=True)
        return False, 0

    # 4) STRICT: sirf EXACT id="add-to-cart-button" (nav-assist ko exclude karo)
    #   (?!...) ke bina bhi kaam karega kyunki hum exact attribute value match kar rahe hain
    button_pattern = r'<input\b[^>]*\bid\s*=\s*["\']add-to-cart-button["\'][^>]*>'
    matches = list(re.finditer(button_pattern, raw_html, re.IGNORECASE))

    if not matches:
        # Fallback: button tag bhi ho sakta hai
        button_pattern2 = r'<button\b[^>]*\bid\s*=\s*["\']add-to-cart-button["\'][^>]*>'
        matches = list(re.finditer(button_pattern2, raw_html, re.IGNORECASE))

    if not matches:
        print("❌ [DEBUG] Asli 'add-to-cart-button' nahi mila -> False, 0", flush=True)
        return False, 0

    is_visible = False
    for match in matches:
        start_idx = max(0, match.start() - 800)
        context = html_lower[start_idx:match.start()]
        button_tag = match.group(0).lower()

        # 🔥 HIDDEN / NAV-ASSIST FILTER
        if "nav-assist" in button_tag or "nav-assist" in context:
            print("⚠️ [DEBUG] nav-assist (hidden) button skip kiya", flush=True)
            continue
        if "display: none" in context or "display:none" in context or "aok-hidden" in context:
            print("⚠️ [DEBUG] display:none context skip", flush=True)
            continue
        if any(x in button_tag for x in ['display: none', 'display:none', 'visibility: hidden', 'aria-hidden="true"', "aria-hidden='true'"]):
            print("⚠️ [DEBUG] hidden button tag skip", flush=True)
            continue
        if 'type="hidden"' in button_tag or "type='hidden'" in button_tag:
            print("⚠️ [DEBUG] type=hidden skip", flush=True)
            continue

        is_visible = True
        break

    if is_visible:
        print("✅ [DEBUG] Asli visible 'Add to Cart' button mil gaya -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Saare buttons hidden/nav-assist the -> False, 0", flush=True)
    return False, 0