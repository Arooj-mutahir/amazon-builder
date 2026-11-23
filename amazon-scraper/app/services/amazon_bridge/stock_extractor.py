import re
from bs4 import BeautifulSoup

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    # ── STEP A: Captcha / Bot page ────────────────────────────────────
    html_lower = raw_html.lower()
    captcha_sigs = ["validatecaptcha", "not a robot", "robot check", "api-services-support@amazon.com"]
    if any(s in html_lower for s in captcha_sigs):
        print("❌ [DEBUG] Captcha/bot page -> False, 0", flush=True)
        return False, 0

    # ── STEP B: BeautifulSoup se DOM parse ────────────────────────────
    try:
        doc = BeautifulSoup(raw_html, "lxml")
    except Exception:
        doc = BeautifulSoup(raw_html, "html.parser")

    # Sirf wohi tags dhoondo jisme ID aur NAME dono hon
    atc_tags = [
        tag for tag in doc.find_all(["input", "button"])
        if (tag.get("id") or "").strip() == "add-to-cart-button"
        and (tag.get("name") or "").strip() == "submit.add-to-cart"
    ]
    
    print(f"🔎 [DEBUG] Real ATC button tags mile: {len(atc_tags)}", flush=True)

    if not atc_tags:
        print("❌ [DEBUG] Asli button DOM mein nahi mila -> False, 0", flush=True)
        return False, 0

    for tag in atc_tags:
        # ── 1. Button ki khud ki Visibility Check ──
        # Agar button par hi display:none ya visibility:hidden hai -> Seedha 0 return karo!
        style = (tag.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            print("❌ [DEBUG] Button hidden hai (display:none/visibility:hidden) -> False, 0", flush=True)
            return False, 0
            
        if (tag.get("type") or "").lower() == "hidden":
            print("❌ [DEBUG] Button type=hidden hai -> False, 0", flush=True)
            return False, 0

        # ── 2. Parents (Wrappers) ki Visibility Check ──
        for parent in tag.parents:
            if not hasattr(parent, "get"):
                break
            pcls   = " ".join(parent.get("class") or []).lower()
            pstyle = (parent.get("style") or "").replace(" ", "").lower()
            pid    = (parent.get("id") or "").lower()

            # Agar koi bhi parent hidden hai -> Seedha 0 return karo!
            if "display:none" in pstyle or "visibility:hidden" in pstyle:
                print("❌ [DEBUG] Button ka parent hidden hai -> False, 0", flush=True)
                return False, 0
            if any(c in pcls for c in ["aok-hidden", "a-hidden", "aok-offscreen"]):
                print("❌ [DEBUG] Button ka parent aok-hidden hai -> False, 0", flush=True)
                return False, 0
            if "nav-assist" in pid or "nav-assist" in pcls:
                print("❌ [DEBUG] Button nav-assist ke andar hai -> False, 0", flush=True)
                return False, 0

        # ✅ Agar button visible hai aur uske koi parents hidden nahi hain
        print("✅ [DEBUG] Real visible ATC button → True, 100", flush=True)
        return True, 100

    return False, 0