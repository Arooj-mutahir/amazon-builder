"""Quick unit tests for extract_stock_from_html — run from amazon-scraper dir."""
import sys
sys.path.insert(0, ".")

from app.services.amazon_bridge.stock_extractor import extract_stock_from_html

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

tests = []

# Pad a minimal HTML string to exceed the 200-char guard
# (Real Amazon pages are always 500KB+; this guard protects against garbage)
_PAD = "<!-- " + "x" * 300 + " -->"

def wrap(body: str) -> str:
    """Wrap body in a full <html> + padding so the length guard passes."""
    return f"<html><head><title>Amazon</title></head><body>{_PAD}{body}</body></html>"

def check(name, html, expected):
    result = extract_stock_from_html(html)
    ok = result == expected
    status = PASS if ok else FAIL
    print(f"  [{status}] {name}: got {result}, expected {expected}")
    tests.append(ok)

print("\n" + "="*60)
print("  STOCK EXTRACTOR TEST SUITE")
print("="*60)

# 1. Empty HTML → guard
check("Empty HTML", "", (False, 0))

# 2. Very short / garbage HTML → guard
check("Too short HTML", "<html>x</html>", (False, 0))

# 3. Captcha page
check("Captcha / bot page", wrap("validateCaptcha robot check"), (False, 0))

# 4. Out of stock text
check("OOS text", wrap("<p>Currently unavailable on Amazon.</p>"), (False, 0))

# 5. Buying-options-only (no ATC button)
check("Buying options only", wrap("<a>See all buying options</a>"), (False, 0))

# 6. nav-assist hidden button (the false-positive from the bug report)
nav_html = wrap(
    '<ul id="nav-assist-shortcuts-container" aria-hidden="true">'
    '<li><input id="add-to-cart-button" type="submit" value="Add to Cart" /></li>'
    "</ul>"
)
check("nav-assist hidden ATC button", nav_html, (False, 0))

# 7. Real visible ATC button
real_html = wrap(
    '<form id="addToCart">'
    '<input id="add-to-cart-button" type="submit" value="Add to Cart" />'
    "</form>"
)
check("Real visible ATC button", real_html, (True, 100))

# 8. ATC button with type=hidden
hidden_type_html = wrap(
    '<input id="add-to-cart-button" type="hidden" value="x" />'
)
check("ATC button type=hidden", hidden_type_html, (False, 0))

# 9. ATC inside display:none parent
hidden_parent_html = wrap(
    '<div style="display:none">'
    '<input id="add-to-cart-button" type="submit" value="Add to Cart" />'
    "</div>"
)
check("ATC inside display:none parent", hidden_parent_html, (False, 0))

# 10. ATC with aria-hidden="true" on itself
aria_html = wrap(
    '<input id="add-to-cart-button" aria-hidden="true" type="submit" value="Add to Cart" />'
)
check("ATC aria-hidden=true", aria_html, (False, 0))

# 11. Real ATC + buying-options text co-exist (real ATC wins)
dual_html = wrap(
    "<p>See all buying options</p>"
    '<form id="addToCart">'
    '<input id="add-to-cart-button" type="submit" value="Add to Cart" />'
    "</form>"
)
check("Real ATC + buying-options co-exist", dual_html, (True, 100))

# 12. noscript-only ATC
noscript_html = wrap(
    "<noscript>"
    '<input id="add-to-cart-button" type="submit" value="Add to Cart" />'
    "</noscript>"
)
check("ATC inside <noscript>", noscript_html, (False, 0))

# 13. ATC with aok-hidden class
aok_html = wrap(
    '<input id="add-to-cart-button" class="aok-hidden" type="submit" value="Add to Cart" />'
)
check("ATC with aok-hidden class", aok_html, (False, 0))

# 14. Signal-5: #availability In Stock + price block
avail_html = wrap(
    '<div id="availability"><span class="a-size-medium a-color-success">In Stock.</span></div>'
    '<span class="a-price"><span class="a-offscreen">$29.99</span></span>'
)
check("Signal-5: #availability In Stock + price", avail_html, (True, 100))

# 15. Signal-5: #availability Out of Stock
avail_oos_html = wrap(
    '<div id="availability"><span>Currently unavailable.</span></div>'
    '<span class="a-price"><span class="a-offscreen">$29.99</span></span>'
)
check("Signal-5: #availability unavailable", avail_oos_html, (False, 0))

# Results
total = len(tests)
passed = sum(tests)
print("="*60)
if passed == total:
    print(f"\n  ALL {total}/{total} TESTS PASSED\n")
else:
    print(f"\n  {passed}/{total} tests passed — {total-passed} FAILED\n")
print("="*60)
