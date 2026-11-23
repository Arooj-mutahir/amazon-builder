# app/services/amazon_bridge/stock_extractor.py

from amazon.parsers import _is_real_atc_visible, soup


def _extract_stock(raw_product: dict, raw_html: str = None):
    """
    Stock extraction — `amazon/parsers.py` ke `_is_real_atc_visible` function
    ko hi use karta hai. Alag se koi logic nahi.
    
    Sirf HTML ke andar Add to Cart button check karta hai.
    Agar button visible hai → True, 100
    Agar button hidden / missing hai → False, 0
    """
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # ── parsers.py ka function use karo ────────────────────────────────
    # `soup()` parsers.py mein already defined hai (BeautifulSoup wrapper)
    try:
        doc = soup(raw_html)
    except Exception as e:
        print(f"❌ [DEBUG] HTML parse fail: {e} -> False, 0", flush=True)
        return False, 0

    is_visible = _is_real_atc_visible(doc, raw_html)

    if is_visible:
        print("✅ [DEBUG] ATC visible -> True, 100", flush=True)
        return True, 100
    else:
        print("❌ [DEBUG] ATC hidden/missing -> False, 0", flush=True)
        return False, 0