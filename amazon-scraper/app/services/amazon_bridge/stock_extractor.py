# app/services/amazon_bridge/stock_extractor.py

import re
from bs4 import BeautifulSoup

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    print(f"✅ [DEBUG] HTML length: {len(raw_html)}", flush=True)

    doc = BeautifulSoup(raw_html, "lxml")

    # ✅ EXACT REQUIREMENT: Sirf woh input/button dhoondo jisme id="add-to-cart-button" AND name="submit.add-to-cart" ho
    candidates = []
    for tag in doc.find_all(["input", "button"]):
        tag_id = (tag.get("id") or "").strip()
        tag_name = (tag.get("name") or "").strip()
        if tag_id == "add-to-cart-button" and tag_name == "submit.add-to-cart":
            candidates.append(tag)

    if not candidates:
        print("❌ [DEBUG] id='add-to-cart-button' AND name='submit.add-to-cart' NOT found -> False, 0", flush=True)
        return False, 0

    print(f"✅ [DEBUG] {len(candidates)} candidate(s) mila with id+name", flush=True)

    # ✅ CHECK: Woh hidden hai ya visible?
    for tag in candidates:
        hidden = False
        reason = None

        # 1. Tag khud pe style="display: none" check
        style = (tag.get("style") or "").replace(" ", "").lower()
        if "display:none" in style:
            hidden, reason = True, "tag self display:none"
        
        # 2. Tag khud pe aok-hidden class check
        elif "aok-hidden" in (tag.get("class") or []):
            hidden, reason = True, "tag self aok-hidden"

        # 3. Parent chain mein display: none check
        if not hidden:
            for parent in tag.parents:
                if not hasattr(parent, "get"):
                    break
                pstyle = (parent.get("style") or "").replace(" ", "").lower()
                pcls   = " ".join(parent.get("class") or []).lower()
                
                if "display:none" in pstyle:
                    hidden, reason = True, "parent style display:none"
                    break
                if "aok-hidden" in pcls:
                    hidden, reason = True, "parent class aok-hidden"
                    break

        # Result
        if hidden:
            print(f"❌ [DEBUG] Candidate hidden ({reason}) -> skip", flush=True)
            continue
        else:
            print("✅ [DEBUG] Button visible (id+name match, no hidden) -> True, 100", flush=True)
            return True, 100

    print("❌ [DEBUG] All candidates hidden -> False, 0", flush=True)
    return False, 0