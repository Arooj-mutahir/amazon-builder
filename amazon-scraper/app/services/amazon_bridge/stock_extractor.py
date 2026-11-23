# app/services/amazon_bridge/stock_extractor.py
import re


def extract_stock_from_html(raw_html: str) -> tuple[bool, int]:
    """
    HTML string input -> (is_available, stock_qty)
    """
    print("\n🔍 [DEBUG] Stock extraction shuru hua...", flush=True)

    if not raw_html or not isinstance(raw_html, str):
        print("❌ [DEBUG] raw_html khaali/invalid -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()

    # 1) BOT / CAPTCHA
    if any(x in html_lower for x in ["validatecaptcha", "not a robot",
                                      "javascript is disabled",
                                      "api-services-support@amazon.com"]):
        print("❌ [BOT/CAPTCHA] -> False, 0", flush=True)
        return False, 0

    # 2) OUT OF STOCK
    if "currently unavailable" in html_lower or "out of stock" in html_lower:
        print("❌ [DEBUG] Out of Stock -> False, 0", flush=True)
        return False, 0

    # 3) OTHER SELLERS
    if ("see all buying options" in html_lower
            or "available at a lower price from other sellers" in html_lower
            or "other sellers on amazon" in html_lower):
        print("❌ [DEBUG] Buying Options / Other Sellers -> False, 0", flush=True)
        return False, 0

    # 4) STRICT VISIBLE BUTTON CHECK
    patterns = [
        r'<input\b[^>]*\bid\s*=\s*["\']add-to-cart-button["\'][^>]*>',
        r'<input\b[^>]*\bid\s*=\s*["\']add-to-cart-button-ubb["\'][^>]*>',
        r'<input\b[^>]*\bname\s*=\s*["\']submit\.add-to-cart["\'][^>]*>',
        r'<button\b[^>]*\bid\s*=\s*["\']add-to-cart-button["\'][^>]*>',
        r'<button\b[^>]*\bid\s*=\s*["\']add-to-cart-button-ubb["\'][^>]*>',
    ]

    matches = []
    for pat in patterns:
        found = list(re.finditer(pat, raw_html, re.IGNORECASE))
        if found:
            print(f"🔎 [DEBUG] Regex matched: {pat[:50]}... ({len(found)})", flush=True)
            matches.extend(found)

    # dedupe
    seen = set()
    unique = []
    for m in matches:
        if m.start() not in seen:
            seen.add(m.start())
            unique.append(m)
    matches = unique

    print(f"🔎 [DEBUG] Total unique regex matches: {len(matches)}", flush=True)

    for idx, match in enumerate(matches):
        start_idx = max(0, match.start() - 800)
        context = raw_html[start_idx:match.start()].lower()
        button_tag = match.group(0).lower()

        if "nav-assist" in button_tag or "nav-assist" in context:
            print(f"   ⚠️ [{idx+1}] nav-assist skip", flush=True)
            continue
        if any(x in context for x in ["display: none", "display:none", "aok-hidden"]):
            print(f"   ⚠️ [{idx+1}] display:none context skip", flush=True)
            continue
        if any(x in button_tag for x in [
            "display: none", "display:none",
            "visibility: hidden",
            'aria-hidden="true"', "aria-hidden='true'",
        ]):
            print(f"   ⚠️ [{idx+1}] hidden tag skip", flush=True)
            continue
        if 'type="hidden"' in button_tag or "type='hidden'" in button_tag:
            print(f"   ⚠️ [{idx+1}] type=hidden skip", flush=True)
            continue

        print(f"   ✅ [{idx+1}] visible button mila", flush=True)
        return True, 100

    print("❌ [DEBUG] Koi visible button nahi -> False, 0", flush=True)
    return False, 0


# ============================================================
# ✅ DICT WRAPPER — main.py ke liye (import error fix)
# ============================================================
def extract_stock_from_data(data: dict) -> tuple[bool, int]:
    """
    main.py se `data` dict aata hai. Isko handle karta hai.
    """
    print("\n🔍 [DEBUG] extract_stock_from_data() called", flush=True)

    if not data or not isinstance(data, dict):
        print("❌ [DEBUG] data invalid -> False, 0", flush=True)
        return False, 0

    # 1) HTML keys
    raw_html = data.get("raw_html") or data.get("html") or data.get("page_source")
    if raw_html and isinstance(raw_html, str):
        return extract_stock_from_html(raw_html)

    # 2) Parsed flag
    if "is_add_to_cart_visible" in data:
        visible = bool(data.get("is_add_to_cart_visible"))
        print(f"🔎 [DEBUG] is_add_to_cart_visible={visible}", flush=True)
        return (True, 100) if visible else (False, 0)

    # 3) availability string
    availability = data.get("availability")
    if isinstance(availability, str) and availability:
        al = availability.lower()
        if "in stock" in al or "in_stock" in al:
            return True, 100
        if "out of stock" in al or "unavailable" in al:
            return False, 0

    # 4) stock number
    stock_val = data.get("stock") or data.get("stock_quantity") or 0
    try:
        si = int(stock_val)
        if si > 0:
            return True, si
    except (TypeError, ValueError):
        pass

    print("❌ [DEBUG] Koi reliable signal nahi -> False, 0", flush=True)
    return False, 0