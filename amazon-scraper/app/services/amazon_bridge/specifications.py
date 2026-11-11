# app/services/amazon_bridge/specifications.py
import re
import html as html_module
from html import escape as _escape


def _extract_specifications(html_doc: str) -> dict:
    if not html_doc:
        return {"html": "", "rows": []}

    specs_section = None
    for spec_id in [
        'productSpecifications_feature_div',
        'productSpecifications',
        'technicalSpecifications_feature_div',
        'technicalSpecifications',
        'productDetails_techSpec_section_1',
        'productDetails_detailBullets_sections1',
        'prodDetails',
    ]:
        m_specs = re.search(
            rf'<div[^>]+id=["\']{spec_id}["\'][^>]*>(.*?)</div>\s*(?=<div[^>]+id=["\'](?:productDetails|detailBullets|similarities|footer)|<footer|$)',
            html_doc, re.DOTALL | re.IGNORECASE,
        )
        if m_specs and re.search(r'\w', m_specs.group(1)):
            specs_section = m_specs.group(1)
            break

    if not specs_section:
        return {"html": "", "rows": []}

    specs_raw = re.sub(r'<!--.*?-->', '', specs_section, flags=re.DOTALL)
    rows = []

    table_m = re.search(r'(<table[^>]*>.*?</table>)', specs_raw, re.DOTALL | re.IGNORECASE)
    if table_m:
        tbl = table_m.group(1)
        tbl = re.sub(r'class="[^"]*"', '', tbl)
        tbl = re.sub(r'style="[^"]*"', '', tbl)
        tbl = re.sub(
            r'<table',
            '<table style="width: 100%; border-collapse: collapse; margin-top: 8px; '
            'font-size: 14px; text-align: left; border: 1px solid #ddd;"',
            tbl, count=1,
        )
        tbl = re.sub(
            r'<th\b',
            '<th style="padding: 10px; background-color: #f7f7f7; '
            'border: 1px solid #ddd; font-weight: bold;"',
            tbl,
        )
        tbl = re.sub(
            r'<td\b',
            '<td style="padding: 8px; border: 1px solid #ddd;"',
            tbl,
        )

        for tr_m in re.finditer(r'<tr[^>]*>(.*?)</tr>', tbl, re.DOTALL | re.IGNORECASE):
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr_m.group(1), re.DOTALL | re.IGNORECASE)
            if len(cells) >= 2:
                name = re.sub(r'<[^>]+>', '', cells[0]).strip()
                value = re.sub(r'<[^>]+>', '', cells[1]).strip()
                if name:
                    rows.append({
                        "name": html_module.unescape(name),
                        "value": html_module.unescape(value),
                    })

        return {"html": tbl, "rows": rows}

    for line in specs_raw.split('\n'):
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if not clean:
            continue
        m_row = re.match(r'^([a-z_]{2,40})\s*[\t]+\s*(.+)$', clean, re.IGNORECASE)
        if not m_row:
            m_row = re.match(r'^([a-z_]{2,40})\s{3,}(.+)$', clean, re.IGNORECASE)
        if m_row:
            name = m_row.group(1).replace("_", " ").title()
            value = m_row.group(2).strip()
            rows.append({"name": name, "value": value})

    if rows:
        trs = ""
        for row in rows:
            trs += (
                f'<tr>'
                f'<td style="padding: 8px; border: 1px solid #ddd; '
                f'font-weight: bold; background-color: #f9f9f9; width: 35%;">'
                f'{_escape(row["name"])}</td>'
                f'<td style="padding: 8px; border: 1px solid #ddd;">'
                f'{_escape(row["value"])}</td>'
                f'</tr>'
            )
        specs_html = (
            '<table style="width: 100%; border-collapse: collapse; '
            'margin-top: 8px; font-size: 14px; text-align: left; '
            'border: 1px solid #ddd;">'
            f'<tbody>{trs}</tbody></table>'
        )
        return {"html": specs_html, "rows": rows}

    return {"html": "", "rows": []}