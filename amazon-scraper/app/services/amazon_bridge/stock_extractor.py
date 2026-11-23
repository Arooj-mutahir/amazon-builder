from bs4 import BeautifulSoup

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)
    if not raw_html: return False, 0

    try:
        doc = BeautifulSoup(raw_html, "lxml")
    except Exception:
        doc = BeautifulSoup(raw_html, "html.parser")

    atc_tags = doc.find_all(id="add-to-cart-button")
    print(f"🔎 [DEBUG] id='add-to-cart-button' wale tags mile: {len(atc_tags)}", flush=True)

    if not atc_tags:
        print("❌ [DEBUG] Asli button nahi mila -> False, 0", flush=True)
        return False, 0

    for tag in atc_tags:
        # 🔍 DEBUG: Style print karo taake pata chale kya hai
        raw_style = tag.get("style") or ""
        print(f"🔍 [DEBUG] Button ki Style: '{raw_style}'", flush=True)

        style = raw_style.replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            print("❌ [DEBUG] Button pe display:none hai -> False, 0", flush=True)
            return False, 0
            
        if (tag.get("type") or "").lower() == "hidden":
            return False, 0

        hidden_parent = False
        for parent in tag.parents:
            if not hasattr(parent, "get"): break
            pstyle = (parent.get("style") or "").replace(" ", "").lower()
            pcls = " ".join(parent.get("class") or []).lower()
            pid = (parent.get("id") or "").lower()

            if "display:none" in pstyle or "visibility:hidden" in pstyle:
                hidden_parent = True; break
            if any(c in pcls for c in ["aok-hidden", "a-hidden", "aok-offscreen"]):
                hidden_parent = True; break
            if "nav-assist" in pid or "nav-assist" in pcls:
                hidden_parent = True; break
            
        if hidden_parent:
            print("❌ [DEBUG] Button ka parent hidden hai -> False, 0", flush=True)
            return False, 0

        print("✅ [DEBUG] Real visible ATC button → True, 100", flush=True)
        return True, 100

    return False, 0