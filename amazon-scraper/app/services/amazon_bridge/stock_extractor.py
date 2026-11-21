import re

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    
    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # 1. Check for "Other Sellers" (Out of Stock signal)
    if 'see all buying options' in html_lower or 'available at a lower price from other sellers' in html_lower:
        print("❌ [DEBUG] 'Other sellers' mila -> False, 0", flush=True)
        return False, 0
    print("✅ [DEBUG] 'Other sellers' check pass", flush=True)

    # 2. Check if "add-to-cart-button" exists in HTML at all
    # Hum strict regex use nahi karenge, bas check karenge ki ID maujood hai ya nahi
    if 'id="add-to-cart-button"' in html_lower or "id='add-to-cart-button'" in html_lower:
        print("✅ [DEBUG] 'add-to-cart-button' ID HTML mein mil gayi.", flush=True)
        
        # 3. Check if the button is hidden
        # Hum button ke aas-paas ka thoda context nikalenge
        # (Kyunki button kabhi <span> ke andar hota hai, kabhi <div> ke andar)
        
        # Button ki position dhundhein
        btn_pos = html_lower.find('add-to-cart-button')
        
        # Uske pehle ke 1500 characters ka context lein (jahan parent div ho sakta hai)
        context_start = max(0, btn_pos - 1500)
        context = html_lower[context_start:btn_pos]
        
        # Agar parent div mein display:none ya aok-hidden hai, toh button hidden hai
        if 'display: none' in context or 'aok-hidden' in context or 'a-hidden' in context:
            print("❌ [DEBUG] Button 'display: none' ya 'hidden' class mein hai -> False, 0", flush=True)
            return False, 0
            
        print("✅ [DEBUG] Button VISIBLE hai (Hidden nahi hai) -> True, 100", flush=True)
        return True, 100
    else:
        print("⚠️ [DEBUG] 'add-to-cart-button' ID nahi mili HTML mein.", flush=True)

    # 4. Fallback Check: Agar button nahi mila par "In Stock" text hai
    if 'primary-availability-message' in html_lower and 'in stock' in html_lower:
        print("✅ [DEBUG] Fallback: 'In Stock' text mila -> True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila -> False, 0", flush=True)
    return False, 0