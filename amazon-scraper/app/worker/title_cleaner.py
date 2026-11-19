# app/worker/title_cleaner.py
import re
import logging

logger = logging.getLogger(__name__)


def _extract_title_excluding_variant_name(main_data: dict) -> str | None:
    """
    Pehli Priority:
    Data source mein agar `titleExcludingVariantName` available hai, to seedha wahi use karein.
    Yeh sabse safe aur accurate Amazon field hai.
    """
    if not isinstance(main_data, dict):
        return None

    # 1. Top-level direct field
    direct_val = main_data.get("titleExcludingVariantName")
    if direct_val and isinstance(direct_val, str) and direct_val.strip():
        return direct_val.strip()

    # 2. Check in summaries (Amazon SP-API / Rainforest / Keepa standard)
    summaries = main_data.get("summaries")
    if isinstance(summaries, list):
        for s in summaries:
            if isinstance(s, dict):
                val = s.get("titleExcludingVariantName")
                if val and isinstance(val, str) and val.strip():
                    return val.strip()
    elif isinstance(summaries, dict):
        val = summaries.get("titleExcludingVariantName")
        if val and isinstance(val, str) and val.strip():
            return val.strip()

    # 3. Check in nested structures (attributes, raw_data, details)
    for sub_key in ("attributes", "raw_data", "details"):
        sub = main_data.get(sub_key)
        if isinstance(sub, dict):
            val = sub.get("titleExcludingVariantName")
            if val and isinstance(val, str) and val.strip():
                return val.strip()

    return None


def _extract_parent_title(main_data: dict) -> str | None:
    """
    Doosri Priority:
    Parent ASIN ka title use karein (relationships / parentAsins se summaries.title pull karein).
    Parent title mein aam tor par color/size nahi hota.
    """
    if not isinstance(main_data, dict):
        return None

    # 1. Direct parent title field agar scraper ne pehle se rakha ho
    parent_title = main_data.get("parent_title") or main_data.get("parentTitle")
    if parent_title and isinstance(parent_title, str) and parent_title.strip():
        return parent_title.strip()

    # 2. Relationships / parentAsins extraction
    relationships = main_data.get("relationships") or {}
    candidates = []

    if isinstance(relationships, dict):
        for key in ("parentAsins", "parent_asins", "parents"):
            val = relationships.get(key)
            if isinstance(val, list):
                candidates.extend(val)
            elif isinstance(val, (dict, str)):
                candidates.append(val)

    # Top-level parent ASIN fields
    for p_key in ("parentAsin", "parent_asin", "parent_asin_data"):
        p_val = main_data.get(p_key)
        if p_val:
            candidates.append(p_val)

    # Candidates se title dhundhein
    for item in candidates:
        if isinstance(item, dict):
            # Check summaries.title
            summaries = item.get("summaries")
            if isinstance(summaries, list):
                for s in summaries:
                    if isinstance(s, dict) and s.get("title") and isinstance(s["title"], str):
                        return s["title"].strip()
            elif isinstance(summaries, dict) and summaries.get("title") and isinstance(summaries["title"], str):
                return summaries["title"].strip()

            # Direct title on dict
            if item.get("title") and isinstance(item["title"], str):
                return item["title"].strip()

        elif isinstance(item, str):
            # Agar item sirf ASIN string ho, to parent_data map check karein
            for p_data_key in ("parent_data", "parent_details"):
                parent_data = main_data.get(p_data_key)
                if isinstance(parent_data, dict) and parent_data.get("title"):
                    return parent_data["title"].strip()

    # Top-level summaries mein parent title check karein
    top_summaries = main_data.get("summaries")
    if isinstance(top_summaries, list):
        for s in top_summaries:
            if isinstance(s, dict):
                p_t = s.get("parentTitle") or s.get("parent_title")
                if p_t and isinstance(p_t, str) and p_t.strip():
                    return p_t.strip()

    return None


def _clean_title_fallback(main_title: str, clean_variants: list) -> str:
    """
    Fallback Priority:
    Agar parent title bhi na mile, to clean_variants[0] (ya main title) ka title use karo,
    lekin usme se color name ko string replace/regex se hata do (case-insensitive,
    extra spaces aur dangling punctuation clean karke).
    """
    # 1. Base title select karein
    base_title = ""
    if clean_variants and isinstance(clean_variants, list) and isinstance(clean_variants[0], dict):
        base_title = clean_variants[0].get("title") or ""
    if not base_title:
        base_title = main_title or ""

    if not base_title or not base_title.strip():
        return "Untitled Product"

    cleaned = base_title.strip()

    # 2. Variants se color names collect karein
    colors_to_remove = set()
    if clean_variants and isinstance(clean_variants, list):
        for v in clean_variants:
            if not isinstance(v, dict):
                continue

            # Direct color field
            if v.get("color") and isinstance(v["color"], str):
                colors_to_remove.add(v["color"].strip())

            # option_values / variant_attributes check karein
            opts = v.get("option_values") or v.get("variant_attributes") or []
            if isinstance(opts, list):
                for opt in opts:
                    if isinstance(opt, dict):
                        name = str(opt.get("name") or opt.get("key") or "").lower()
                        val = str(opt.get("value") or opt.get("val") or "").strip()
                        # Sirf Color/Colour wale attributes uthayein
                        if any(c in name for c in ("color", "colour", "shade", "style")) and val:
                            colors_to_remove.add(val)

            # option1/option2/option3 check (agar string hai aur size/number nahi)
            for opt_key in ("option1", "option2", "option3", "color_name"):
                val = v.get(opt_key)
                if val and isinstance(val, str):
                    val = val.strip()
                    # Skip pure sizes/numbers jaise '8', '8.5', 'XL', '10'
                    if not re.match(r'^(?:[0-9]+(?:\.[0-9]+)?|[x|s|m|l|xl|xxl]+)$', val, re.IGNORECASE):
                        if len(val.split()) <= 4:
                            colors_to_remove.add(val)

    # Lambe color names pehle replace karein (e.g. "Dark Navy Blue" before "Blue")
    sorted_colors = sorted(colors_to_remove, key=len, reverse=True)

    for color in sorted_colors:
        if not color or len(color) < 2:
            continue

        esc = re.escape(color)
        # a. Brackets ke andar color: (Black) ya [Black]
        cleaned = re.sub(rf'\s*[\(\[]\s*{esc}\s*[\)\]]', '', cleaned, flags=re.IGNORECASE)
        # b. Separator ke sath: ", Black" ya " - Black" ya " / Black" ya " | Black"
        cleaned = re.sub(rf'\s*[,:\-\/\|]\s*{esc}\b', '', cleaned, flags=re.IGNORECASE)
        # c. Color followed by separator: "Black - " ya "Black, "
        cleaned = re.sub(rf'\b{esc}\s*[,:\-\/\|]\s*', ' ', cleaned, flags=re.IGNORECASE)
        # d. Standalone word match
        cleaned = re.sub(rf'\b{esc}\b', '', cleaned, flags=re.IGNORECASE)

    # 3. Cleanup: dangling brackets, extra commas/hyphens/spaces
    cleaned = re.sub(r'\(\s*\)|\[\s*\]', '', cleaned)                 # Empty () ya []
    cleaned = re.sub(r'[\s,\-:\/\|]{2,}', ' ', cleaned)               # Double separators
    cleaned = re.sub(r'^\s*[,:\-\/\|\.]+\s*', '', cleaned)            # Leading punctuation
    cleaned = re.sub(r'\s*[,:\-\/\|\.]+\s*$', '', cleaned)            # Trailing punctuation
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()                    # Multi spaces

    return cleaned if cleaned else base_title.strip()


def get_clean_product_title(main_data: dict, clean_variants: list = None) -> str:
    """
    Shopify Product Title Resolver (Priority Order):
    1. Pehli Priority: titleExcludingVariantName
    2. Doosri Priority: Parent ASIN ka title (relationships / parentAsins -> summaries.title)
    3. Fallback: clean_variants[0] title minus color name
    """
    if not isinstance(main_data, dict):
        return "Untitled Product"

    clean_variants = clean_variants or []

    # 1. Pehli Priority
    title_excl = _extract_title_excluding_variant_name(main_data)
    if title_excl:
        logger.info(f"Using Priority 1 title (titleExcludingVariantName): {title_excl}")
        return title_excl

    # 2. Doosri Priority
    parent_title = _extract_parent_title(main_data)
    if parent_title:
        logger.info(f"Using Priority 2 title (Parent ASIN Title): {parent_title}")
        return parent_title

    # 3. Fallback Priority
    original_title = main_data.get("title") or ""
    fallback_title = _clean_title_fallback(original_title, clean_variants)
    logger.info(f"Using Priority 3 title (Fallback color-cleaned): {fallback_title}")
    return fallback_title


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
