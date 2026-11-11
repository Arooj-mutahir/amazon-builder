# test.py
import asyncio
import re
from amazon import fetch

def extract_stock_final(html):
    if not html:
        return False, 0

    html_lower = html.lower()

    # 1. "See All Buying Options" -> 0
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("🔍 DEBUG: 'Other sellers' mila (Out of Stock)")
        return False, 0

    # 2. Asli button ka exact pattern (ignore 'Currently unavailable')
    real_button_pattern = r'<span[^>]*\bid=["\']submit\.add-to-cart["\'][^>]*>.*?<input[^>]*\bid=["\']add-to-cart-button["\'][^>]*>'
    
    match = re.search(real_button_pattern, html, re.IGNORECASE | re.DOTALL)
    
    if match:
        print("🔍 DEBUG: Asli button mila! Ab parent check kar rahe hain...")
        # Check karein ke kya yeh span kisi hidden parent ke andar hai
        start_idx = max(0, match.start() - 1000)
        context = html_lower[start_idx:match.start()]
        
        if 'display: none' in context or 'aok-hidden' in context:
            print("🔍 DEBUG: Parent 'display:none' mein hai (Out of Stock)")
            return False, 0
            
        print("🔍 DEBUG: Button visible hai (In Stock)")
        return True, 100

    # 3. Fallback: "In Stock" text
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("🔍 DEBUG: Asli button nahi mila, par 'In Stock' text hai")
        return True, 100

    print("🔍 DEBUG: Kuch nahi mila (Default 0)")
    return False, 0


async def main():
    asin = "B0BL79TPT3"
    print(f"🚀 Fetching {asin}...")
    
    html = await asyncio.to_thread(
        fetch.page, "US", f"/dp/{asin}", {"th": "1", "psc": "1"}
    )
    
    print(f"✅ HTML Size: {len(html)} bytes")
    
    if len(html) < 2400000:
        print("❌ Amazon ne CAPTCHA bheja hai! IP abhi bhi blocked hai.")
        return
        
    is_available, stock_qty = extract_stock_final(html)
    print(f"🎯 RESULT: is_available={is_available}, stock_qty={stock_qty}")

if __name__ == "__main__":
    asyncio.run(main())