import re
from bs4 import BeautifulSoup

def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()

    # ── STEP A: Captcha / Bot page ────────────────────────────────────
    captcha_sigs = ["validatecaptcha", "not a robot", "robot check", "api-services-support@amazon.com"]
    if any(s in html_lower for s in captcha_sigs):
        print("❌ [DEBUG] Captcha/bot page -> False, 0", flush=True)
        return False, 0

    # ── STEP B: BeautifulSoup se DOM parse ────────────────────────────
    try:
        doc = BeautifulSoup(raw_html, "lxml")
    except Exception:
        doc = BeautifulSoup(raw_html, "html.parser")

    # 1. PEHLE AVAILABILITY TEXT CHECK KARO (Sabse pakka tarika)
    # Agar Amazon khud keh raha hai "Currently unavailable" ya "Out of Stock", toh sidha 0.
    availability_div = doc.find(id="availability")
    if availability_div:
        avail_text = availability_div.get_text(strip=True).lower()
        if any(oos in avail_text for oos in ["currently unavailable", "out of stock", "nicht verfügbar"]):
            print(f"❌ [DEBUG] Page pe OOS text mila ('{avail_text}') -> False, 0", flush=True)
            return False, 0

    # 2. AGAR TEXT NAHI MILA, TOH BUTTON CHECK KARO
    atc_tags = doc.find_all(attrs={"id": "add-to-cart-button"})
    print(f"🔎 [DEBUG] id='add-to-cart-button' tags mile: {len(atc_tags)}", flush=True)

    for tag in atc_tags:
        name_attr = (tag.get("name") or "").strip()
        
        # Sirf asli button accept karo (nav-assist ko ignore karo)
        if name_attr != "submit.add-to-cart":
            continue

        # ── Button ki Visibility Check (Tag khud) ──
        style = (tag.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            continue
        if (tag.get("type") or "").lower() == "hidden":
            continue

        # ── Parents ki Visibility Check (Wrappers) ──
        skip = False
        for parent in tag.parents:
            if not hasattr(parent, "get"):
                break
            pcls   = " ".join(parent.get("class") or []).lower()
            pstyle = (parent.get("style") or "").replace(" ", "").lower()
            pid    = (parent.get("id") or "").lower()

            # Agar parent ya uske andar ka koi bhi hissa hidden hai
            if "display:none" in pstyle or "visibility:hidden" in pstyle:
                skip = True; break
            if any(c in pcls for c in ["aok-hidden", "a-hidden", "aok-offscreen"]):
                skip = True; break
            # Buybox agar disabled hai
            if "buybox" in pid and "disabled" in pcls:
                skip = True; break
            
        if skip:
            continue

        # ✅ Sab pass ho gaya -> Button visible hai
        print("✅ [DEBUG] Real visible ATC button → True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Button hidden hai ya nahi mila → False, 0", flush=True)
    return False, 0