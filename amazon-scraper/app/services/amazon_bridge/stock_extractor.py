import re
from bs4 import BeautifulSoup


def _extract_stock(raw_product: dict, raw_html: str = None):
    print("\n🔍 [DEBUG] _extract_stock shuru hua...", flush=True)

    if not raw_html:
        print("❌ [DEBUG] raw_html khaali hai -> False, 0", flush=True)
        return False, 0

    html_lower = raw_html.lower()
    print(f"✅ [DEBUG] HTML length: {len(html_lower)}", flush=True)

    # ── STEP A: Captcha / Bot page ────────────────────────────────────
    captcha_sigs = ["validatecaptcha", "not a robot", "robot check", "api-services-support@amazon.com"]
    if any(s in html_lower for s in captcha_sigs):
        print("❌ [DEBUG] Captcha/bot page -> False, 0", flush=True)
        return False, 0

    # ── STEP B: BeautifulSoup se DOM check (robust) ───────────────────
    try:
        doc = BeautifulSoup(raw_html, "lxml")
    except Exception as e:
        print(f"⚠️ [DEBUG] lxml fail ({e}), html.parser try...", flush=True)
        doc = BeautifulSoup(raw_html, "html.parser")

    # id="add-to-cart-button" wale saare tags
    atc_tags = doc.find_all(attrs={"id": "add-to-cart-button"})
    print(f"🔎 [DEBUG] id='add-to-cart-button' tags mile: {len(atc_tags)}", flush=True)

    for tag in atc_tags:
        name_attr = (tag.get("name") or "").strip()
        print(f"   → tag: <{tag.name}> name='{name_attr}'", flush=True)

        # name="submit.add-to-cart" hona chahiye (strict per requirement)
        if name_attr != "submit.add-to-cart":
            print("   ⏭️  name mismatch → skip", flush=True)
            continue

        # ── Visibility check: tag khud ──
        style = (tag.get("style") or "").replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            print("   ⏭️  tag style hidden → skip", flush=True)
            continue
        if (tag.get("aria-hidden") or "").lower() == "true":
            print("   ⏭️  aria-hidden=true → skip", flush=True)
            continue
        if (tag.get("type") or "").lower() == "hidden":
            print("   ⏭️  type=hidden → skip", flush=True)
            continue
        tag_cls = " ".join(tag.get("class") or []).lower()
        if any(c in tag_cls for c in ["aok-hidden", "a-hidden", "aok-offscreen"]):
            print("   ⏭️  tag aok-hidden class → skip", flush=True)
            continue

        # ── Visibility check: parents ──
        skip = False
        for parent in tag.parents:
            if not hasattr(parent, "get"):
                break
            pid    = (parent.get("id") or "").lower()
            pcls   = " ".join(parent.get("class") or []).lower()
            pstyle = (parent.get("style") or "").replace(" ", "").lower()

            if "nav-assist" in pid or "nav-assist" in pcls:
                print("   ⏭️  inside nav-assist → skip", flush=True)
                skip = True; break
            if "display:none" in pstyle or "visibility:hidden" in pstyle:
                print("   ⏭️  ancestor hidden style → skip", flush=True)
                skip = True; break
            if any(c in pcls for c in ["aok-hidden", "a-hidden", "aok-offscreen"]):
                print("   ⏭️  ancestor aok-hidden → skip", flush=True)
                skip = True; break
        if skip:
            continue

        # ✅ Real visible ATC button
        print("✅ [DEBUG] Real visible ATC button → True, 100", flush=True)
        return True, 100

    # ── STEP C: Fallback — raw HTML mein id+name dono ek hi tag pe ──
    print("⚠️ [DEBUG] BS4 se visible button nahi mila, regex fallback...", flush=True)
    fallback = re.search(
        r'<input[^>]*\bid=["\']add-to-cart-button["\'][^>]*\bname=["\']submit\.add-to-cart["\'][^>]*>',
        raw_html, re.IGNORECASE
    ) or re.search(
        r'<input[^>]*\bname=["\']submit\.add-to-cart["\'][^>]*\bid=["\']add-to-cart-button["\'][^>]*>',
        raw_html, re.IGNORECASE
    )
    if fallback:
        tag_html = fallback.group(0).replace(" ", "").lower()
        if "display:none" in tag_html or "visibility:hidden" in tag_html or "type=hidden" in tag_html:
            print("❌ [DEBUG] Fallback: button hidden → False, 0", flush=True)
            return False, 0
        print("✅ [DEBUG] Fallback: button visible → True, 100", flush=True)
        return True, 100

    print("❌ [DEBUG] Kuch bhi nahi mila → False, 0", flush=True)
    return False, 0