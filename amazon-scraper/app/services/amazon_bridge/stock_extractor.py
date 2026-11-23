# app/services/amazon_bridge/stock_extractor.py
"""
Stock extractor — parsers.py ka parsed `data` dict use karta hai.

Logic source of truth:
  amazon/parsers.py → _is_real_atc_visible(doc, html_text)
      → data["is_add_to_cart_visible"]  True / False

Yahan sirf us value ko padh kar return karo.
Koi fallback nahi, koi re-parsing nahi, koi BeautifulSoup import nahi.
"""
import os
from typing import Tuple

_DEBUG = os.getenv("AMZ_STOCK_DEBUG", "0").strip() == "1"


def extract_stock_from_data(data: dict) -> Tuple[bool, int]:
    """
    parsers.py se aaye parsed `data` dict se stock decide karta hai.

    Rule:
      is_add_to_cart_visible = True  →  (True, 100)   product directly buyable
      is_add_to_cart_visible = False →  (False, 0)    out of stock / 3rd-party only

    Koi aur signal/fallback nahi — woh sab parsers._is_real_atc_visible mein
    already handle ho gaye hain (captcha, OOS text, nav-assist, hidden, buying-options).
    """
    is_atc = bool(data.get("is_add_to_cart_visible", False))

    if is_atc:
        print("✅ [STOCK] is_add_to_cart_visible=True → True, 100", flush=True)
        return True, 100

    print("❌ [STOCK] is_add_to_cart_visible=False → False, 0", flush=True)
    return False, 0


# ── Kept for backward compatibility (called nowhere now) ─────────────────────
def extract_stock_from_html(raw_html: str) -> Tuple[bool, int]:
    """Legacy path — should not be called in normal flow."""
    print("⚠️ [STOCK] extract_stock_from_html called — this is a legacy path. "
          "Ensure main.py uses extract_stock_from_data(data) instead.", flush=True)
    return False, 0
