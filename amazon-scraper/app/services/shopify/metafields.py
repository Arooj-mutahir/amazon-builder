# app/services/shopify/metafields.py
import re
from html import escape as _escape, unescape as _unescape
from .client import shopify_graphql


# ============================================================
# DESCRIPTION SANITIZER
# ============================================================

def _sanitize_amazon_description(html: str) -> str:
    """
    Amazon A+ content / description se JS, CSS, tracking pixels
    aur widget junk hataata hai. Real text + safe HTML tags chhod deta hai.
    """
    if not html:
        return ""

    # 1. Poora <script>, <style>, <noscript>, <iframe> blocks remove
    html = re.sub(r'<script\b[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style\b[^>]*>.*?</style>',   '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript\b[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<iframe\b[^>]*>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 2. Amazon ke inline JS widget calls hataao
    html = re.sub(r'if\s*\(\s*\)\s*\{[^}]*\}', '', html)
    html = re.sub(r'P\.when\([^)]*\)\s*\.\s*execute\([^)]*\);?', '', html)
    html = re.sub(r'runtime\.registerCardFactory\([^)]*\)', '', html)

    # 3. Bache hue lone CSS-rule lines hataao (e.g. ._YnVmZ_xxx{...})
    html = re.sub(r'(?m)^\s*\._[A-Za-z0-9_]+\s*\{[^}]*\}\s*$', '', html)

    # 4. HTML entities decode — &lt; → <, &amp; → &
    html = _unescape(html)

    # 5. Extra blank lines collapse
    html = re.sub(r'\n{3,}', '\n\n', html).strip()

    return html


# ============================================================
# DESCRIPTION BUILDER
# ============================================================

def _build_description_with_metafields(
    description_html: str,   
    bullets: list,           
    details: dict,           
    size_chart_html: str = None, 
    reviews: list = None,        
) -> str:
    
    sections = []

    # ── Section 1: About this item ───────────────────────────
    if bullets:
        bullet_items = "\n".join(
            f"  <li>{_escape(str(b).strip())}</li>"
            for b in bullets if str(b).strip()
        )
        if bullet_items:
            sections.append(
                "<h3>About this item</h3>\n"
                f"<ul>\n{bullet_items}\n</ul>"
            )

    # ── Section 2: Product Description ───────────────────────
    desc = _sanitize_amazon_description(description_html or "")
    if desc:
        desc = re.sub(
            r'^\s*<h[1-4][^>]*>\s*(?:Product\s+Description|From\s+the\s+Manufacturer)\s*</h[1-4]>\s*',
            '', desc, flags=re.IGNORECASE
        )
        desc = re.sub(r'<table[^>]*>.*?</table>', '', desc, flags=re.DOTALL | re.IGNORECASE)
        desc = re.sub(r'<div[^>]*class="[^"]*brand-story[^"]*"[^>]*>.*?</div>', '', desc, flags=re.DOTALL | re.IGNORECASE)
        desc = desc.strip()

        # Safety: clean ke baad sirf symbols / CSS / brackets bache ho toh section skip
        visible = re.sub(r'<[^>]+>', '', desc).strip()
        visible = re.sub(r'[\{\}\(\)\.\,\:\;_\-\s\|]+', '', visible)

        if len(visible) >= 20:
            sections.append(
                "<h3>Product Description</h3>\n"
                f"{desc}"
            )

    # ── Section 3: Size Chart (BUTTON & MODAL) ───────────────
    if size_chart_html and size_chart_html.strip():
        clean_chart = size_chart_html.strip()
        
        # ✅ Button aur Modal ka HTML
        size_chart_block = f"""
        <div style="margin: 20px 0; text-align: center;">
            <button id="sizeChartBtn" style="background-color: #000; color: #fff; padding: 10px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px;">
                📏 View Size Chart
            </button>
        </div>

        <div id="sizeChartModal" style="display: none; position: fixed; z-index: 9999; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6);">
            <div style="background-color: #fff; margin: 5% auto; padding: 20px; border-radius: 8px; width: 90%; max-width: 800px; position: relative; max-height: 80vh; overflow-y: auto;">
                <span id="closeSizeChart" style="position: absolute; right: 20px; top: 10px; font-size: 28px; font-weight: bold; cursor: pointer; color: #333;">&times;</span>
                <h3 style="text-align: center; margin-bottom: 20px; font-size: 22px; color: #000;">Size Chart</h3>
                <div style="overflow-x: auto;">
                    {clean_chart}
                </div>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var modal = document.getElementById('sizeChartModal');
                var btn = document.getElementById('sizeChartBtn');
                var span = document.getElementById('closeSizeChart');

                if (btn && modal && span) {{
                    btn.onclick = function() {{ modal.style.display = 'block'; }}
                    span.onclick = function() {{ modal.style.display = 'none'; }}
                    window.onclick = function(event) {{
                        if (event.target == modal) {{ modal.style.display = 'none'; }}
                    }}
                }}
            }});
        </script>
        """
        sections.append(size_chart_block)

    # ── Section 4: Product Specifications ─────────────────────
    if details:
        rows = []
        for key, value in list(details.items())[:20]:
            if not value or not str(value).strip():
                continue
            safe_key   = _escape(str(key).strip())
            safe_value = _escape(str(value).strip())
            rows.append(
                f"<tr>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #e0e0e0;"
                f"font-weight:bold;width:35%;background:#f9f9f9;'>{safe_key}</td>"
                f"<td style='padding:8px 12px;border-bottom:1px solid #e0e0e0;'>{safe_value}</td>"
                f"</tr>"
            )
        if rows:
            table_html = (
                "<table style='width:100%;border-collapse:collapse;"
                "font-size:14px;margin-top:8px;'>\n"
                "  <tbody>\n    "
                + "\n    ".join(rows)
                + "\n  </tbody>\n</table>"
            )
            sections.append(
                "<h3>Product Specifications</h3>\n"
                f"{table_html}"
            )

    # ── Section 5: Customer Reviews ───────────────────────────
    if reviews:
        cards_html = []
        for r in reviews[:15]:
            author = r.get("author") or r.get("name") or "Amazon Customer"
            try:
                rating = float(r.get("rating") or 5.0)
            except (ValueError, TypeError):
                rating = 5.0
            title = r.get("title") or ""
            text = r.get("text") or ""
            images = r.get("images") or []
            videos = r.get("videos") or []
            verified = bool(r.get("verified") or r.get("is_verified_purchase"))

            full_stars = min(5, max(0, int(round(rating))))
            stars_str = "★" * full_stars + "☆" * (5 - full_stars)

            verified_badge = (
                '<span style="margin-left: 8px; font-size: 12px; color: #c45500; font-weight: 600; '
                'background: #fff4e5; padding: 2px 8px; border-radius: 4px; border: 1px solid #ffd8a8; '
                'display: inline-block;">✓ Verified Purchase</span>'
                if verified else ''
            )

            title_html = (
                f'<div style="font-weight: 700; font-size: 15px; color: #1a202c; margin-top: 6px;">'
                f'{_escape(title)}</div>'
                if title else ""
            )

            paras = [p.strip() for p in text.split("\n") if p.strip()]
            if paras:
                paras_html = "".join(
                    f'<p style="margin: 6px 0; font-size: 14px; line-height: 1.5; color: #333333;">{_escape(p)}</p>'
                    for p in paras
                )
            else:
                paras_html = ""

            imgs_html = ""
            if images:
                img_tags = "".join(
                    f'<a href="{_escape(u)}" target="_blank" rel="noopener noreferrer" style="display: inline-block; margin: 4px;">'
                    f'<img src="{_escape(u)}" alt="Customer review photo" style="width: 100px; height: 100px; object-fit: cover; border-radius: 6px; border: 1px solid #e2e8f0; display: block;" />'
                    f'</a>'
                    for u in images[:10]
                )
                imgs_html = f'<div style="display: flex; flex-wrap: wrap; margin-top: 10px;">{img_tags}</div>'

            vids_html = ""
            if videos:
                vid_tags = "".join(
                    f'<div style="margin-top: 8px; max-width: 480px;">'
                    f'<video controls style="max-width: 100%; border-radius: 6px; display: block; border: 1px solid #e2e8f0;">'
                    f'<source src="{_escape(v)}" />Your browser does not support the video tag.</video></div>'
                    for v in videos[:5]
                )
                vids_html = vid_tags

            card = (
                '<div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 12px; background: #ffffff;">\n'
                f'  <div style="display: flex; align-items: center; flex-wrap: wrap; margin-bottom: 4px;">\n'
                f'    <span style="font-weight: 600; font-size: 14px; color: #1a202c;">{_escape(author)}</span>\n'
                f'    {verified_badge}\n'
                f'  </div>\n'
                f'  <div style="display: flex; align-items: center; margin: 4px 0;">\n'
                f'    <span style="color: #f59e0b; font-size: 16px; letter-spacing: 2px;">{stars_str}</span>\n'
                f'    <span style="font-size: 13px; color: #4a5568; margin-left: 6px; font-weight: 600;">{rating:.1f} / 5</span>\n'
                f'  </div>\n'
                f'  {title_html}\n'
                f'  {paras_html}\n'
                f'  {imgs_html}\n'
                f'  {vids_html}\n'
                '</div>'
            )
            cards_html.append(card)

        if cards_html:
            reviews_content = "\n".join(cards_html)
            sections.append(
                "<h3>Customer Reviews</h3>\n"
                f"<div style='margin-top: 12px;'>\n{reviews_content}\n</div>"
            )

    if not sections:
        return ""

    return "\n\n".join(sections)


# ============================================================
# METAFIELDS HELPER
# ============================================================

async def set_product_metafields_smart(
    shop: str, access_token: str, product_id: str, raw_details: dict
):
    """
    Push product details to Shopify as metafields (namespace: amazon_details).
    Capped at 20 items to stay safely under Shopify's 25-metafield-per-call limit.
    """
    if not raw_details:
        return

    def _mf_type(value: str) -> str:
        v = value.strip()
        if re.match(r"^\d+$", v):
            return "number_integer"
        try:
            float(v)
            return "number_decimal"
        except ValueError:
            pass
        if v.lower() in ("true", "false"):
            return "boolean"
        if v.startswith("http://") or v.startswith("https://"):
            return "url"
        return "single_line_text_field"

    if not str(product_id).startswith("gid://"):
        product_id = f"gid://shopify/Product/{product_id}"

    metafields_payload = []
    for key, value in list(raw_details.items())[:20]:
        if not value or not str(value).strip():
            continue
        key_handle = re.sub(r'[^a-zA-Z0-9_]', '_', str(key).lower().strip())[:64]
        if not key_handle:
            continue
        metafields_payload.append({
            "ownerId":   product_id,
            "namespace": "amazon_details",
            "key":       key_handle,
            "type":      _mf_type(str(value).strip()),
            "value":     str(value).strip(),
        })

    if not metafields_payload:
        return

    mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { id key namespace }
        userErrors  { field message }
      }
    }
    """
    try:
        result = await shopify_graphql(shop, access_token, mutation,
                                       {"metafields": metafields_payload})
        user_errors = (result.get("data", {}).get("metafieldsSet") or {}).get("userErrors") or []
        if "errors" in result or user_errors:
            print(f"⚠️  Metafields errors: {result.get('errors') or user_errors}", flush=True)
        else:
            print(f"✅ {len(metafields_payload)} metafield(s) saved successfully", flush=True)
    except Exception as exc:
        print(f"⚠️  Metafields exception: {exc}", flush=True)