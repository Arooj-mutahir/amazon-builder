import sys
import re
import json

# Ensure project app is in sys.path
sys.path.insert(0, ".")

from app.services.amazon_bridge import extract_top_reviews
from amazon import fetch, sites, parsers

def extract_asin(input_str: str) -> str:
    """Extracts 10-character ASIN from raw ASIN or Amazon URL."""
    input_str = input_str.strip()
    m = re.search(r'/(?:dp|product-reviews|gp/product)/([A-Z0-9]{10})', input_str, re.I)
    if m:
        return m.group(1).upper()
    m2 = re.search(r'\b([A-Z0-9]{10})\b', input_str, re.I)
    if m2:
        return m2.group(1).upper()
    return input_str.upper()

def debug_product_reviews(asin_or_url: str):
    asin = extract_asin(asin_or_url)
    print(f"\n=======================================================")
    print(f"🔍 DEBUGGING AMAZON REVIEWS FOR ASIN: {asin}")
    print(f"=======================================================")

    site = sites.site("US")
    print(f"📡 Fetching Amazon product page for /dp/{asin}...")
    
    html = fetch.page("US", f"/dp/{asin}", {"th": "1", "psc": "1"}, referer=f"https://www.amazon.com/s?k={asin}")
    treatment = parsers.review_treatment(html)
    has_inline = 'data-hook="review"' in html or 'customer_review-' in html
    print(f"📄 Response length: {len(html):,} bytes")
    print(f"🧪 Amazon A/B Treatment: {treatment} | Has inline reviews in HTML: {has_inline}")

    if not has_inline and treatment == "T1":
        print(f"⚠️ Amazon assigned treatment 'T1' (empty medley). Dropping session and retrying once...")
        fetch.drop_session("US", "page")
        try:
            retry_html = fetch.page("US", f"/dp/{asin}", {"th": "1", "psc": "1"}, referer=f"https://www.amazon.com/s?k={asin}")
            if 'data-hook="review"' in retry_html or 'customer_review-' in retry_html:
                html = retry_html
                print(f"✅ Retry got reviews HTML!")
        except Exception as e:
            print(f"Retry error: {e}")

    # Fallback from parser if any
    raw_data = parsers.product_page(html, site)
    fallback_revs = raw_data.get("top_reviews") or []
    print(f"📦 Parsers top_reviews found: {len(fallback_revs)}")

    # Extract with regex
    reviews = extract_top_reviews(html, limit=15, fallback_reviews=fallback_revs)
    print(f"\n⭐ TOTAL REVIEWS FOUND BY extract_top_reviews: {len(reviews)}")

    if reviews:
        print("\n--- FIRST REVIEW DETAILS ---")
        first = reviews[0]
        for k, v in first.items():
            if k == "text" and len(str(v)) > 150:
                print(f"  {k}: {v[:150]}... [total {len(v)} chars]")
            else:
                print(f"  {k}: {v}")
    else:
        print("\n❌ No reviews could be extracted from this page HTML.")

    print(f"=======================================================\n")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "B00939I7EK"
    debug_product_reviews(target)

