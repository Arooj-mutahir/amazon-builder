# app/services/amazon_bridge/size_chart.py
import re
import json
import html as html_module
from html import escape as _escape


def _extract_size_chart(html_text: str, images_list: list = None) -> str:
    if not html_text:
        return ""

    table_match = re.search(
        r'(<table[^>]+(?:class|id)=["\'][^"\']*(?:size[-_]?chart|size[-_]?guide)[^"\']*["\'][^>]*>.*?</table>)',
        html_text, re.DOTALL | re.IGNORECASE,
    )
    if not table_match:
        div_match = re.search(
            r'<div[^>]+id=["\'](?:size[-_]?chart[-_]?content|sizeChartModal|aplus-size[-_]?chart)[^"\']*["\'][^>]*>(.*?)</div>',
            html_text, re.DOTALL | re.IGNORECASE,
        )
        if div_match and '<table' in div_match.group(1).lower():
            table_match = re.search(r'(<table[^>]*>.*?</table>)', div_match.group(1), re.DOTALL | re.IGNORECASE)

    if table_match:
        tbl_html = table_match.group(1)
        tbl_html = re.sub(r'class="[^"]*"', '', tbl_html)
        tbl_html = re.sub(r'style="[^"]*"', '', tbl_html)
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
        return tbl_html

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