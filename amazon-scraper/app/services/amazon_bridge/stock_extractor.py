import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # --- 1. "Other sellers" check ---
    if ('see all buying options' in html_lower
            or 'available at a lower price from other sellers' in html_lower):
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0
    print("✅ [DEBUG] 'Other sellers' check pass", flush=True)

    # --- 2. Find the add-to-cart input (loose match) ---
    # Amazon uses id="add-to-cart-button" OR name="submit.add-to-cart"
    btn_match = re.search(
        r'<input[^>]*\bid=["\']add-to-cart-button["\'][^>]*>',
        raw_html, re.IGNORECASE
    )

    if btn_match:
        btn_start = btn_match.start()
        btn_end = btn_match.end()

        # --- 2a. Inline hidden check on the button itself ---
        button_tag = raw_html[btn_start:btn_end]
        if re.search(r'style=["\'][^"\']*display\s*:\s*none', button_tag, re.I) \
           or 'aok-hidden' in button_tag:
            print("❌ [DEBUG] Button khud hidden hai -> False, 0", flush=True)
            return False, 0

        # --- 2b. Parent hidden check — look BACK up to 3000 chars ---
        # Capture the last opened div/span wrapper before the button
        lookback = raw_html[max(0, btn_start - 3000):btn_start]

        # Find the nearest enclosing container (the feature div)
        parent_match = re.search(
            r'<div[^>]*id=["\']addToCart_feature_div["\'][^>]*>',
            lookback, re.IGNORECASE
        )
        if parent_match:
            parent_tag = parent_match.group(0)
            if re.search(r'style=["\'][^"\']*display\s*:\s*none', parent_tag, re.I) \
               or 'aok-hidden' in parent_tag:
                print("❌ [DEBUG] Parent div hidden (addToCart_feature_div) -> False, 0", flush=True)
                return False, 0

        # Fallback: if any 'display:none' / aok-hidden appears in the
        # immediate 800-char window before the button, treat as hidden
        window = lookback[-800:]
        if re.search(r'display\s*:\s*none', window, re.I) or 'aok-hidden' in window:
            print("❌ [DEBUG] Immediate parent hidden (display:none / aok-hidden) -> False, 0", flush=True)
            return False, 0

        print("✅ [DEBUG] Button visible -> True, 100", flush=True)
        return True, 100

    print("⚠️ [DEBUG] add-to-cart-button input NAHI mila", flush=True)

    # --- 3. If the button is entirely absent, DO NOT trust 'in stock' text ---
    # Amazon always renders add-to-cart-button for buyable products.
    # Absence = out of stock / unavailable.
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("⚠️ [DEBUG] 'In Stock' text mila LEKIN button nahi -> False, 0", flush=True)
        return False, 0

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0