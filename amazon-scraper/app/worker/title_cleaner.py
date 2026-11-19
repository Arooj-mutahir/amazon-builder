# app/worker/title_cleaner.py
import re
import logging

logger = logging.getLogger(__name__)


def strip_variant_info_from_title(title: str, clean_variants: list = None, main_data: dict = None) -> str:
    """
    Amazon ka original title hi rakhta hai, kisi doosre source se replace nahi karta.
    Sirf us title ke andar mojood variant/color/size ki information ko saaf karta hai.
    """
    if not title or not isinstance(title, str):
        return ""

    cleaned = title.strip()
    if not cleaned:
        return ""

    # 1. Variants se saari variant values (colors, sizes, styles) collect karein
    variant_values = set()

    # clean_variants se collect karein
    if clean_variants and isinstance(clean_variants, list):
        for v in clean_variants:
            if not isinstance(v, dict):
                continue
            # Direct color/size fields
            for k in ("color", "size", "style", "color_name", "size_name"):
                val = v.get(k)
                if val and isinstance(val, str) and val.strip():
                    variant_values.add(val.strip())

            # option_values / variant_attributes (e.g. Color: Black Nubuck, Size: 7.5)
            opts = v.get("option_values") or v.get("variant_attributes") or []
            if isinstance(opts, list):
                for opt in opts:
                    if isinstance(opt, dict):
                        val = opt.get("value") or opt.get("val")
                        if val and isinstance(val, str) and val.strip():
                            variant_values.add(val.strip())

    # main_data se bhi details check karein (selected variant attributes)
    if main_data and isinstance(main_data, dict):
        details = main_data.get("details") or {}
        if isinstance(details, dict):
            for k in ("Color", "Colour", "Size", "Style"):
                val = details.get(k)
                if val and isinstance(val, str) and val.strip():
                    variant_values.add(val.strip())

    # 2. Explicit Amazon labels hatao (jaise Color: Black, Size: 8, Style: Modern)
    cleaned = re.sub(
        r'[\s,\-:\/\|]*\b(?:Color|Colour|Size|Style)\s*:\s*[^,\(\)\[\]]+',
        '', cleaned, flags=re.IGNORECASE
    )

    # 3. Common size patterns (jaise "Size 7.5", "Size: 7", "8.5 M US", "9 US")
    cleaned = re.sub(
        r'[\s,\-:\/\|]*\b(?:Size|Sz)\s*[:\s]*[0-9]+(?:\.[0-9]+)?(?:\s*(?:US|UK|EU|M|W))?\b',
        '', cleaned, flags=re.IGNORECASE
    )

    # 4. Bracketed contents agar unme sirf variant values hain ya variant keyword hai
    # e.g. (Black, Size 7.5), [Black], (Red Nubuck)
    def _clean_bracket(m):
        inside = m.group(1).strip()
        inside_lower = inside.lower()
        if any(v.lower() == inside_lower or f" {v.lower()} " in f" {inside_lower} " for v in variant_values if len(v) >= 2):
            return ""
        if re.search(r'\b(?:color|colour|size|sz)\b', inside, re.I):
            return ""
        return m.group(0)

    cleaned = re.sub(r'\s*\(([^)]+)\)', _clean_bracket, cleaned)
    cleaned = re.sub(r'\s*\[([^\]]+)\]', _clean_bracket, cleaned)

    # 5. Longest variant values pehle replace karein (e.g. "Black Nubuck" before "Black")
    sorted_values = sorted([v for v in variant_values if len(v) >= 2], key=len, reverse=True)

    for val in sorted_values:
        esc = re.escape(val)
        # a. Brackets ke andar: (val) ya [val]
        cleaned = re.sub(rf'\s*[\(\[]\s*{esc}\s*[\)\]]', '', cleaned, flags=re.IGNORECASE)
        # b. Separator ke sath: ", val" ya " - val" ya " / val" ya " | val"
        cleaned = re.sub(rf'\s*[,:\-\/\|]\s*{esc}\b', '', cleaned, flags=re.IGNORECASE)
        # c. val followed by separator: "val - " ya "val, "
        cleaned = re.sub(rf'\b{esc}\s*[,:\-\/\|]\s*', ' ', cleaned, flags=re.IGNORECASE)
        # d. Word boundary at the end of title
        cleaned = re.sub(rf'\s+[-–—]?\s*\b{esc}\b\s*$', '', cleaned, flags=re.IGNORECASE)

    # 6. Clean up leftover punctuation, dangling hyphens/commas, multiple spaces
    cleaned = re.sub(r'\(\s*\)|\[\s*\]', '', cleaned)                 # Empty () or []
    cleaned = re.sub(r'[\s,\-:\/\|]{2,}', ' ', cleaned)               # Double separators
    cleaned = re.sub(r'^\s*[,:\-\/\|\.]+\s*', '', cleaned)            # Leading punctuation
    cleaned = re.sub(r'\s*[,:\-\/\|\.]+\s*$', '', cleaned)            # Trailing punctuation
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()                    # Multi spaces

    # Agar galti se saara title hi empty ho gaya ho, fallback to original title
    return cleaned if cleaned else title.strip()


def reorder_variants_for_default(clean_variants: list, selected_asin: str | None) -> list:
    """
    Variant Ordering (Shopify Default Variant):
    URL wala selected child ASIN ko match karke index 0 par shift karein,
    taake Shopify usi ko default variant banaye.
    Agar match na mile, to variants jaisa hai waisa hi rakho (fallback = pehla variant).
    """
    if not clean_variants or not isinstance(clean_variants, list):
        return []

    if not selected_asin or not isinstance(selected_asin, str):
        return clean_variants

    selected_asin = selected_asin.strip()

    # ASIN match dhoondo
    match_index = None
    for idx, v in enumerate(clean_variants):
        if isinstance(v, dict) and v.get("asin") == selected_asin:
            match_index = idx
            break

    # Index 0 par shift karein agar index 0 se aage mila
    if match_index is not None and match_index > 0:
        selected_v = clean_variants[match_index]
        reordered = [selected_v] + clean_variants[:match_index] + clean_variants[match_index + 1:]
        logger.info(f"Reordered variants: ASIN {selected_asin} moved to index 0 (Shopify default variant)")
        return reordered
    elif match_index == 0:
        logger.info(f"Selected ASIN {selected_asin} is already at index 0")
        return clean_variants
    else:
        logger.warning(f"Selected ASIN {selected_asin} not found in variants, keeping default order")
        return clean_variants
