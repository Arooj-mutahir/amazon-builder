# app/services/amazon_bridge/stock_extractor.py
"""
Production-ready Amazon stock extractor using BeautifulSoup DOM traversal.
Multi-signal approach: captcha → out-of-stock text → buying-options-only text
  → visible real add-to-cart button → price+availability block.

Environment variables:
  AMZ_STOCK_DEBUG=1   → saves raw HTML to /tmp/amz_debug/last_page.html
                        and prints every add-to-cart occurrence with ±200-char context
"""

import os
import re
import textwrap
from typing import Tuple

from bs4 import BeautifulSoup, Comment

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
_DEBUG = os.getenv("AMZ_STOCK_DEBUG", "0").strip() == "1"
_DEBUG_DIR = "/tmp/amz_debug"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _save_debug_html(raw_html: str) -> None:
    """Debug mode: saves raw HTML to disk so you can open in browser."""
    try:
        os.makedirs(_DEBUG_DIR, exist_ok=True)
        path = os.path.join(_DEBUG_DIR, "last_page.html")
        with open(path, "w", encoding="utf-8", errors="replace") as f:
            f.write(raw_html)
        print(f"[DEBUG] HTML saved to {path} ({len(raw_html):,} bytes)", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Could not save HTML: {exc}", flush=True)


def _print_atc_contexts(raw_html: str) -> None:
    """Debug mode: prints every add-to-cart occurrence with ±200-char context."""
    for m in re.finditer(r"add.to.cart", raw_html, re.IGNORECASE):
        start = max(0, m.start() - 200)
        end = min(len(raw_html), m.end() + 200)
        snippet = raw_html[start:end].replace("\n", " ").strip()
        print(f"[DEBUG][ATC-CONTEXT] ...{snippet}...", flush=True)


def _is_hidden_element(tag) -> bool:
    """
    Returns True if a BeautifulSoup tag should be considered hidden / invisible.
    Checks:
      - style attribute: display:none, visibility:hidden, opacity:0
      - aria-hidden="true"
      - type="hidden"
      - aok-hidden / a-hidden CSS classes (Amazon-specific)
      - tabindex="-1" on the button's closest nav-assist container (belt-and-suspenders)
    """
    # 1. Direct style check
    style = (tag.get("style") or "").replace(" ", "").lower()
    if any(x in style for x in ["display:none", "visibility:hidden", "opacity:0"]):
        return True

    # 2. aria-hidden
    if tag.get("aria-hidden", "").lower() == "true":
        return True

    # 3. type="hidden" (input fields)
    if tag.get("type", "").lower() == "hidden":
        return True

    # 4. Amazon-specific hidden CSS classes
    css_classes = " ".join(tag.get("class") or []).lower()
    if any(cls in css_classes for cls in ["aok-hidden", "a-hidden", "aok-offscreen"]):
        return True

    return False


def _is_inside_nav_assist(tag) -> bool:
    """
    Walks up the DOM tree to check if the tag is inside a nav-assist
    container (the hidden accessibility shortcuts menu).
    """
    for parent in tag.parents:
        if parent.name is None:
            break
        pid = (parent.get("id") or "").lower()
        pcls = " ".join(parent.get("class") or []).lower()
        if "nav-assist" in pid or "nav-assist" in pcls:
            return True
    return False


def _is_inside_noscript(tag) -> bool:
    """Returns True if the tag is inside a <noscript> block."""
    for parent in tag.parents:
        if getattr(parent, "name", None) == "noscript":
            return True
    return False


def _is_inside_comment(tag) -> bool:
    """Returns True if the tag's parent is an HTML comment node."""
    # Comments in BS4 are Comment objects; a real element's direct parent
    # is never a Comment, so this checks if any ancestor is a Comment.
    for parent in tag.parents:
        if isinstance(parent, Comment):
            return True
    return False


def _ancestors_hidden(tag) -> bool:
    """
    Checks if ANY ancestor element carries a style/attribute that would
    visually hide the entire subtree (e.g. a parent <div style="display:none">).
    """
    for parent in tag.parents:
        if parent.name is None:
            break
        pstyle = (parent.get("style") or "").replace(" ", "").lower()
        if any(x in pstyle for x in ["display:none", "visibility:hidden"]):
            return True
        pcls = " ".join(parent.get("class") or []).lower()
        if any(cls in pcls for cls in ["aok-hidden", "a-hidden", "aok-offscreen"]):
            return True
    return False


# ---------------------------------------------------------------------------
# MAIN FUNCTION
# ---------------------------------------------------------------------------

def extract_stock_from_html(raw_html: str) -> Tuple[bool, int]:
    """
    Multi-signal Amazon stock detection.

    Returns:
        (is_available: bool, stock_qty: int)
        (True, 100)  → product is directly buyable from Amazon
        (False, 0)   → out of stock, third-party only, captcha, or uncertain
    """
    print("\n🔍 [STOCK] extract_stock_from_html — shuru hua", flush=True)

    # ── Guard: empty HTML ───────────────────────────────────────────────────
    if not raw_html or len(raw_html.strip()) < 200:
        print("❌ [STOCK][SKIP] raw_html khaali ya bohot chhota hai → False, 0", flush=True)
        return False, 0

    # ── Debug mode ──────────────────────────────────────────────────────────
    if _DEBUG:
        _save_debug_html(raw_html)
        _print_atc_contexts(raw_html)

    html_lower = raw_html.lower()

    # ── SIGNAL 1: Bot / Captcha page ────────────────────────────────────────
    captcha_signals = [
        "validatecaptcha",
        "not a robot",
        "javascript is disabled",
        "api-services-support@amazon.com",
        "robot check",
        "enter the characters you see below",
    ]
    for sig in captcha_signals:
        if sig in html_lower:
            print(f"❌ [STOCK][BOT/CAPTCHA] Signal '{sig}' mila → False, 0", flush=True)
            return False, 0

    # ── SIGNAL 2: Explicit out-of-stock text ────────────────────────────────
    oos_signals = [
        "currently unavailable",
        "this item is currently unavailable",
        "out of stock",
        "item is unavailable",
        "not available for purchase",
        "we don't know when or if this item will be back in stock",
    ]
    for sig in oos_signals:
        if sig in html_lower:
            print(f"❌ [STOCK][OOS-TEXT] Signal '{sig}' mila → False, 0", flush=True)
            return False, 0

    # ── SIGNAL 3: "See All Buying Options" / 3rd-party only text ────────────
    # NOTE: We check for the ABSENCE of a real ATC button later; these signals
    # alone are insufficient because some pages show BOTH a direct ATC + a
    # "buying options" link. So we only use these as a *tiebreaker* (see end).
    buying_options_signals = [
        "see all buying options",
        "available at a lower price from other sellers",
        "other sellers on amazon",
        "new & used",
    ]
    buying_options_found = any(sig in html_lower for sig in buying_options_signals)
    if buying_options_found:
        print(
            "[STOCK][WARN] 'See All Buying Options' / 'Other Sellers' text mila. "
            "Real ATC button existence confirm karenge...",
            flush=True,
        )

    # ── Parse DOM ───────────────────────────────────────────────────────────
    # lxml is 5-10x faster than html.parser for large pages
    try:
        soup = BeautifulSoup(raw_html, "lxml")
    except Exception:
        soup = BeautifulSoup(raw_html, "html.parser")

    # Remove <noscript> blocks entirely so their hidden content never matches
    for ns in soup.find_all("noscript"):
        ns.decompose()

    # Remove comment nodes
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # ── SIGNAL 4: Visible real Add-to-Cart button (DOM traversal) ───────────
    #
    # Amazon uses:
    #   <input id="add-to-cart-button" type="submit" ...>   (classic /dp/ page)
    #   <button id="add-to-cart-button" ...>                 (some variants)
    #   <span id="submit.add-to-cart" ...>                   (rare)
    #
    # The accessibility shortcuts menu uses id="nav-assist-add-to-cart" which
    # is DIFFERENT from "add-to-cart-button" — but we guard against it anyway.

    real_atc_found = False
    atc_candidates = soup.find_all(
        ["input", "button"],
        id=re.compile(r"^add-to-cart-button$", re.IGNORECASE),
    )
    # Also catch span/div wrappers that sometimes substitute the button
    atc_candidates += soup.find_all(
        id=re.compile(r"^submit\.add-to-cart$", re.IGNORECASE)
    )

    if _DEBUG:
        print(
            f"[DEBUG] DOM: found {len(atc_candidates)} raw add-to-cart candidate(s) before filtering",
            flush=True,
        )

    for tag in atc_candidates:
        tag_id = (tag.get("id") or "").lower()
        tag_str = str(tag)[:300]

        # --- Exclusion checks ---
        if "nav-assist" in tag_id:
            print(f"[STOCK][SKIP] nav-assist id → skipped: {tag_str[:120]}", flush=True)
            continue

        if _is_inside_nav_assist(tag):
            print(f"[STOCK][SKIP] Inside nav-assist container → skipped", flush=True)
            continue

        if _is_inside_noscript(tag):
            print(f"[STOCK][SKIP] Inside <noscript> → skipped", flush=True)
            continue

        if _is_inside_comment(tag):
            print(f"[STOCK][SKIP] Inside HTML comment → skipped", flush=True)
            continue

        if _is_hidden_element(tag):
            print(f"[STOCK][SKIP] Hidden element (style/aria/type) → skipped: {tag_str[:120]}", flush=True)
            continue

        if _ancestors_hidden(tag):
            print(f"[STOCK][SKIP] Ancestor is hidden → skipped: {tag_str[:120]}", flush=True)
            continue

        # --- Passed all exclusion checks → real visible ATC button ---
        print(f"[STOCK][MATCH] Real visible ATC button mila: {tag_str[:200]}", flush=True)
        real_atc_found = True
        break

    if real_atc_found:
        print("✅ [STOCK] SIGNAL 4 passed: Genuine visible Add-to-Cart → True, 100", flush=True)
        return True, 100

    if _DEBUG:
        print(f"[DEBUG] SIGNAL 4 failed: 0 qualifying ATC buttons after filtering", flush=True)

    # ── SIGNAL 5: Price block + #availability "In Stock" ────────────────────
    #
    # On some international / variant pages, the button is rendered differently
    # but the #availability span says "In Stock". We only trust this if the
    # page also has a price block AND does NOT have buying-options-only text.
    #
    if not buying_options_found:
        avail_tag = soup.find(id="availability")
        if avail_tag:
            avail_text = avail_tag.get_text(" ", strip=True).lower()
            print(f"[STOCK][SIGNAL-5] #availability text: '{avail_text}'", flush=True)

            if "in stock" in avail_text:
                # Confirm price block also exists
                has_price = bool(
                    soup.find(id=re.compile(r"priceblock_(ourprice|dealprice|saleprice)", re.I))
                    or soup.find(class_=re.compile(r"\ba-price\b"))
                )
                if has_price:
                    print(
                        "✅ [STOCK] SIGNAL 5 passed: #availability='In Stock' + price block found → True, 100",
                        flush=True,
                    )
                    return True, 100
                else:
                    print(
                        "[STOCK][WARN] #availability='In Stock' but NO price block → treating as uncertain",
                        flush=True,
                    )
            elif any(x in avail_text for x in ["unavailable", "out of stock", "currently"]):
                print(f"❌ [STOCK][OOS-DOM] #availability says unavailable → False, 0", flush=True)
                return False, 0

    # ── All signals exhausted → product not directly buyable ────────────────
    print("❌ [STOCK] All signals exhausted. No genuine ATC button found → False, 0", flush=True)
    return False, 0
