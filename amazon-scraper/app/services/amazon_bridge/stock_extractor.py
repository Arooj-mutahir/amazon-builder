# app/services/amazon_bridge/stock_extractor.py
"""
Amazon stock extractor — existing parsers.py ka parsed data use karta hai.

Parsing ALREADY ho chuki hai `amazon/parsers.py` ki `product_page()` mein:
  - data["is_add_to_cart_visible"]  → True/False (regex + context checks)
  - data["availability"]            → {"text": ..., "is_in_stock": True/False, "quantity_left": int|None}
  - data["price"]                   → {"amount": float, ...}

Yahan hum sirf un parsed fields ko padh kar decision lete hain.
BeautifulSoup ya HTML re-parse karna yahan bilkul nahi kiya.
"""

import os
import re
from typing import Tuple

_DEBUG = os.getenv("AMZ_STOCK_DEBUG", "0").strip() == "1"


# ---------------------------------------------------------------------------
# Main function — called from amazon_bridge/main.py
# ---------------------------------------------------------------------------

def extract_stock_from_html(raw_html: str) -> Tuple[bool, int]:
    """
    DEPRECATED PATH — raw_html se kuch nahi karna.
    Seedha `extract_stock_from_data(data)` use karo jab parsed data ho.

    Yeh function sirf us case ke liye raha hua hai jab main.py ke paas
    raw_html ho lekin data dict na ho (should not happen in normal flow).
    Is case mein bhi hum sirf text signals check karte hain — no BS parsing.
    """
    print("⚠️ [STOCK] extract_stock_from_html called (raw path). "
          "Prefer extract_stock_from_data(data) instead.", flush=True)

    if not raw_html or len(raw_html.strip()) < 200:
        print("❌ [STOCK][SKIP] raw_html khaali ya bohot chhota hai → False, 0", flush=True)
        return False, 0

    if _DEBUG:
        _save_debug_html(raw_html)
        _print_atc_contexts(raw_html)

    html_lower = raw_html.lower()

    # Signal 1: Bot / Captcha
    captcha_signals = [
        "validatecaptcha", "not a robot", "api-services-support@amazon.com",
        "robot check", "enter the characters you see below",
    ]
    for sig in captcha_signals:
        if sig in html_lower:
            print(f"❌ [STOCK][BOT/CAPTCHA] '{sig}' mila → False, 0", flush=True)
            return False, 0

    # Signal 2: Explicit OOS text
    oos_signals = [
        "currently unavailable", "out of stock",
        "we don't know when or if this item will be back in stock",
        "not available for purchase",
    ]
    for sig in oos_signals:
        if sig in html_lower:
            print(f"❌ [STOCK][OOS-TEXT] '{sig}' mila → False, 0", flush=True)
            return False, 0

    # Signal 3: buying-options-only text (no direct ATC)
    buying_opts = [
        "see all buying options",
        "available at a lower price from other sellers",
        "other sellers on amazon",
    ]
    if any(sig in html_lower for sig in buying_opts):
        # Check if a real ATC button regex also exists
        atc_match = re.search(
            r'<input[^>]*id=["\']add-to-cart-button["\'][^>]*>', raw_html, re.IGNORECASE
        )
        if not atc_match:
            print("❌ [STOCK][BUYING-OPTS] 'See All Buying Options' + no ATC button → False, 0", flush=True)
            return False, 0
        # ATC button tag found — check it's not nav-assist
        tag = atc_match.group(0).lower()
        ctx_start = max(0, atc_match.start() - 800)
        ctx = html_lower[ctx_start:atc_match.start()]
        if "nav-assist" in ctx or "nav-assist" in tag:
            print("❌ [STOCK][BUYING-OPTS] ATC is nav-assist hidden → False, 0", flush=True)
            return False, 0
        if any(x in tag for x in ["display:none", "display: none", "aria-hidden=\"true\"", "type=\"hidden\""]):
            print("❌ [STOCK][BUYING-OPTS] ATC tag is hidden → False, 0", flush=True)
            return False, 0
        if any(x in ctx for x in ["display:none", "display: none", "aok-hidden"]):
            print("❌ [STOCK][BUYING-OPTS] ATC context is hidden → False, 0", flush=True)
            return False, 0

    # Signal 4: id="add-to-cart-button" strict regex
    atc_pattern = r'<input[^>]*id=["\']add-to-cart-button["\'][^>]*>'
    for match in re.finditer(atc_pattern, raw_html, re.IGNORECASE):
        tag = match.group(0).lower()
        ctx_start = max(0, match.start() - 800)
        ctx = html_lower[ctx_start:match.start()]

        if "nav-assist" in tag or "nav-assist" in ctx:
            print("[STOCK][SKIP] nav-assist → skipped", flush=True)
            continue
        if any(x in tag for x in ["display:none", "display: none", "visibility:hidden",
                                   'aria-hidden="true"', "type=\"hidden\""]):
            print(f"[STOCK][SKIP] Hidden tag attr → skipped", flush=True)
            continue
        if any(x in ctx for x in ["display:none", "display: none", "aok-hidden"]):
            print(f"[STOCK][SKIP] Hidden context → skipped", flush=True)
            continue

        print(f"✅ [STOCK][MATCH] Real ATC button → True, 100", flush=True)
        return True, 100

    print("❌ [STOCK] No genuine ATC button → False, 0", flush=True)
    return False, 0


# ---------------------------------------------------------------------------
# PREFERRED function — parsed data dict use karta hai (no re-parsing)
# ---------------------------------------------------------------------------

def extract_stock_from_data(data: dict) -> Tuple[bool, int]:
    """
    Parsers.py ki `product_page()` se aaye hue parsed `data` dict se
    stock decide karta hai. Koi HTML parse nahi karta — sirf dict fields padho.

    Fields used (sab parsers.py mein already computed hain):
      data["is_add_to_cart_visible"]  → bool
      data["availability"]            → {text, is_in_stock, quantity_left} | None
      data["price"]                   → {amount, ...} | None
    """
    print("\n🔍 [STOCK] extract_stock_from_data — shuru hua", flush=True)

    # ── SIGNAL 1: parsers.py ka is_add_to_cart_visible ───────────────────
    # Yeh already captcha + OOS + nav-assist + hidden checks ke baad set hai
    is_atc = data.get("is_add_to_cart_visible")
    if is_atc is True:
        print("✅ [STOCK] SIGNAL-1: is_add_to_cart_visible=True → True, 100", flush=True)
        return True, 100

    if is_atc is False:
        print("[STOCK] SIGNAL-1: is_add_to_cart_visible=False. Availability check karenge...", flush=True)

    # ── SIGNAL 2: availability dict (parsers._availability) ──────────────
    avail = data.get("availability") or {}
    avail_text = (avail.get("text") or "").lower().strip()
    is_in_stock = avail.get("is_in_stock")  # True | False | None
    qty_left = avail.get("quantity_left")   # int | None

    print(f"[STOCK] SIGNAL-2: availability text='{avail_text}', is_in_stock={is_in_stock}, qty_left={qty_left}", flush=True)

    if is_in_stock is False:
        print("❌ [STOCK] SIGNAL-2: availability says NOT in stock → False, 0", flush=True)
        return False, 0

    if is_in_stock is True:
        # Only trust "In Stock" if price also exists (confirms real buybox)
        has_price = bool((data.get("price") or {}).get("amount"))
        if has_price:
            stock = qty_left if qty_left and qty_left > 0 else 100
            print(f"✅ [STOCK] SIGNAL-2: In stock + price exists → True, {stock}", flush=True)
            return True, stock
        else:
            print("[STOCK] SIGNAL-2: availability=In Stock but NO price → uncertain, treating as OOS", flush=True)

    # ── SIGNAL 3: "See All Buying Options" / "Other Sellers" text ─────────
    # parsers.py ne buybox field parse ki hai
    buybox = data.get("buybox") or {}
    if buybox:
        # Agar buybox mein koi seller hai to product buyable ho sakta hai
        # lekin Amazon direct nahi bech raha — hum conservatively False return karte hain
        print("[STOCK] SIGNAL-3: Buybox has 3rd-party seller (Amazon direct nahi) → False, 0", flush=True)
        return False, 0

    # ── SIGNAL 4: Price block exist karta hai + availability uncertain ────
    # Agar availability neutral (None) hai lekin price exist karta hai
    # aur koi explicit OOS text nahi — toh "likely available" treat karein
    if avail_text and any(k in avail_text for k in ["usually ships", "available", "in stock"]):
        has_price = bool((data.get("price") or {}).get("amount"))
        if has_price:
            print(f"✅ [STOCK] SIGNAL-4: Availability text '{avail_text}' + price → True, 100", flush=True)
            return True, 100

    # ── All signals exhausted ─────────────────────────────────────────────
    print("❌ [STOCK] All signals exhausted → False, 0", flush=True)
    return False, 0


# ---------------------------------------------------------------------------
# Debug helpers (only called when AMZ_STOCK_DEBUG=1)
# ---------------------------------------------------------------------------

_DEBUG_DIR = "/tmp/amz_debug"


def _save_debug_html(raw_html: str) -> None:
    try:
        os.makedirs(_DEBUG_DIR, exist_ok=True)
        path = os.path.join(_DEBUG_DIR, "last_page.html")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(raw_html)
        print(f"[DEBUG] HTML saved → {path} ({len(raw_html):,} bytes)", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Save failed: {exc}", flush=True)


def _print_atc_contexts(raw_html: str) -> None:
    for m in re.finditer(r"add.to.cart", raw_html, re.IGNORECASE):
        start = max(0, m.start() - 200)
        end = min(len(raw_html), m.end() + 200)
        snippet = raw_html[start:end].replace("\n", " ").strip()
        print(f"[DEBUG][ATC-CONTEXT] ...{snippet}...", flush=True)
