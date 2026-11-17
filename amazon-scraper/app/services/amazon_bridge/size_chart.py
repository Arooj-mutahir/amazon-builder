# app/services/amazon_bridge/size_chart.py
import re
import json
import html as html_module
from html import escape as _escape

def _is_real_size_chart(tbl_html: str) -> bool:
    """Check karein ki table sach mein size chart hai ya nahi."""
    if not tbl_html:
        return False
    
    lower_html = tbl_html.lower()
    
    # ✅ Size chart mein yeh words hone chahiye (kam se kam 2)
    size_keywords = [
        "size", "bust", "waist", "length", "hip", "chest", 
        "shoulder", "sleeve", "inseam", "shoe", "foot", 
        "us size", "uk size", "eu size", "measurement"
    ]
    keyword_count = sum(1 for kw in size_keywords if kw in lower_html)
    
    # ✅ Junk code na ho
    junk_keywords = [
        "_ynvmz_", "_multi-brand-video-", "grid-gap", 
        "border-right-width", "box-shadow", "@media", 
        "webkit", "aok-sfs", "position:", "display:grid"
    ]
    junk_count = sum(1 for kw in junk_keywords if kw in lower_html)
    
    # Agar 2 se zyada size keywords hain aur 1 se kam junk hai, toh valid hai
    return keyword_count >= 2 and junk_count == 0

def _clean_table_html(tbl_html: str) -> str:
    """Table ko clean karein (junk attributes hataayein)."""
    tbl_html = re.sub(r'class="[^"]*"', '', tbl_html)
    tbl_html = re.sub(r'style="[^"]*"', '', tbl_html)
    tbl_html = re.sub(r'id="[^"]*"', '', tbl_html)
    tbl_html = re.sub(
        r'<table',
        '<table style="width: 100%; border-collapse: collapse; margin-top: 10px; '
        'font-size: 14px; text-align: center; border: 1px solid #ddd;"',
        tbl_html, count=1,
    )
    tbl_html = re.sub(
        r'<th\b',
        '<th style="padding: 10px; background-color: #f7f7f7; '
        'border: 1px solid #ddd; font-weight: bold;"',
        tbl_html,
    )
    tbl_html = re.sub(
        r'<td\b',
        '<td style="padding: 8px; border: 1px solid #ddd;"',
        tbl_html,
    )
    # Junk tags hataayein
    tbl_html = re.sub(r'<script\b[^>]*>.*?</script>', '', tbl_html, flags=re.DOTALL | re.IGNORECASE)
    tbl_html = re.sub(r'<style\b[^>]*>.*?</style>', '', tbl_html, flags=re.DOTALL | re.IGNORECASE)
    return tbl_html

def _extract_size_chart(html_text: str, images_list: list = None) -> str:
    if not html_text:
        return ""

    # ✅ 1. Table match (class/id mein size-chart, size-guide)
    table_match = re.search(
        r'(<table[^>]+(?:class|id)=["\'][^"\']*(?:size[-_]?chart|size[-_]?guide)[^"\']*["\'][^>]*>.*?</table>)',
        html_text, re.DOTALL | re.IGNORECASE,
    )
    if table_match:
        candidate = table_match.group(1)
        if _is_real_size_chart(candidate):
            return _clean_table_html(candidate)

    # ✅ 2. Hidden div match
    div_match = re.search(
        r'<div[^>]+id=["\'](?:size[-_]?chart[-_]?content|sizeChartModal|aplus-size[-_]?chart)[^"\']*["\'][^>]*>(.*?)</div>',
        html_text, re.DOTALL | re.IGNORECASE,
    )
    if div_match and '<table' in div_match.group(1).lower():
        inner_table = re.search(r'(<table[^>]*>.*?</table>)', div_match.group(1), re.DOTALL | re.IGNORECASE)
        if inner_table and _is_real_size_chart(inner_table.group(1)):
            return _clean_table_html(inner_table.group(1))

    # ✅ 3. JSON match
    json_match = re.search(
        r'data-a-state=\'\{"key":"f2-fit-size-chart-popover"\}\'>(\{.*?\})</script>',
        html_text, re.DOTALL,
    )
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            chart_data = data.get("sizeChartData") or data.get("chartData")
            if chart_data and isinstance(chart_data, dict):
                headers = chart_data.get("headers") or []
                rows = chart_data.get("rows") or []
                if headers and rows:
                    # ✅ Verify karein ki headers mein size keywords hain
                    header_str = " ".join(str(h).lower() for h in headers)
                    if any(kw in header_str for kw in ["size", "bust", "waist", "length", "hip", "chest"]):
                        th_html = "".join(
                            f"<th style='padding: 10px; background-color: #f7f7f7; "
                            f"border: 1px solid #ddd; font-weight: bold;'>{_escape(str(h))}</th>"
                            for h in headers
                        )
                        tr_html = ""
                        for row in rows:
                            tds = "".join(
                                f"<td style='padding: 8px; border: 1px solid #ddd;'>"
                                f"{_escape(str(cell))}</td>"
                                for cell in row
                            )
                            tr_html += f"<tr>{tds}</tr>\n"
                        return (
                            f"<table style='width: 100%; border-collapse: collapse; "
                            f"margin-top: 10px; font-size: 14px; text-align: center; "
                            f"border: 1px solid #ddd;'>\n"
                            f"<thead><tr>{th_html}</tr></thead>\n"
                            f"<tbody>\n{tr_html}</tbody>\n</table>"
                        )
        except Exception:
            pass

    # ✅ 4. Image match
    if images_list:
        for itm in images_list:
            url = itm if isinstance(itm, str) else (itm.get("link") or itm.get("large") or "")
            if any(term in url.lower() for term in [
                "size_chart", "sizechart", "size-chart", "sizeguide", "size_guide",
            ]):
                if url.startswith("//"):
                    url = "https:" + url
                elif not url.startswith("http"):
                    url = "https://" + url
                return (
                    f'<img src="{url}" alt="Size Chart" '
                    f'style="max-width: 100%; height: auto; display: block; '
                    f'margin: 16px auto; border-radius: 4px; border: 1px solid #eee;" />'
                )

    return ""