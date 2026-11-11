# app/services/amazon_bridge/description.py
import re
import json
import logging
import html as html_module
from html import escape as _escape

# ✅ YEH 2 LINES ADD KI GAYI HAIN
logger = logging.getLogger(__name__)

def _extract_img_url(tag):
    src = None
    for attr in ["data-src", "data-a-hires", "data-original", "data-old-hires", "src"]:
        m = re.search(rf'{attr}=["\']([^"\']+)["\']', tag, re.I)
        if m:
            val = m.group(1).strip()
            if not any(bad in val.lower() for bad in [
                "grey-pixel", "pixel.gif", "transparent-pixel", "data:image",
                "loading", "spinner", "/icons/", "sprite", "logo-",
                "nav-", "star-", "badge-", "prime-", "a-button", "checkmark",
            ]):
                src = val
                break
    if not src:
        return None
    if src.startswith("//"):
        src = "https:" + src
    elif not src.startswith("http"):
        src = "https://" + src
    src = re.sub(r'\._[A-Za-z0-9_,-]+(?=\.[a-zA-Z]+$)', '', src, flags=re.IGNORECASE)
    return src


def _extract_clean_description(html_doc: str, fallback_desc: str = "") -> str:
    if not html_doc:
        return ""

    boundary = r'(?=<div[^>]+id=["\'](?:productDetails_feature_div|productDetails|technicalSpecifications_feature_div|technicalSpecifications|detailBullets_feature_div|customerReviews|ask_feature_div|reviewsMedley|sims-consolidated-2_feature_div|similarities_feature_div|sp_detail|sponsoredProducts|footer|productSpecifications_feature_div|productSpecifications)["\']|<footer|$)'

    # STEP 1: #productDescription se TEXT
    text_chunk = ""
    m_prod = re.search(
        rf'<div[^>]+id=["\']productDescription["\'][^>]*>(.*?){boundary}',
        html_doc, re.DOTALL | re.IGNORECASE,
    )
    if m_prod:
        candidate = m_prod.group(1)
        candidate = re.sub(r'<!--.*?-->', '', candidate, flags=re.DOTALL)
        candidate = re.sub(r'!-{2,}[^\n]*', '', candidate)
        candidate = re.sub(r'/?\w+\s*&gt;', ' ', candidate)
        candidate = re.sub(r'/?\w+\s*&lt;', ' ', candidate)
        candidate = candidate.replace("&amp;gt;", "&gt;")
        candidate = candidate.replace("&amp;lt;", "&lt;")
        candidate = html_module.unescape(candidate)
        candidate = re.sub(r'/?\w+>', ' ', candidate)
        candidate = re.sub(r'/?\w+<', ' ', candidate)
        candidate = re.sub(r'(?<=\s)[<>](?=\s)', ' ', candidate)
        candidate = re.sub(r'(?<=\s)[<>]$', '', candidate, flags=re.MULTILINE)
        candidate = re.sub(r'^[<>](?=\s)', '', candidate, flags=re.MULTILINE)

        candidate = re.sub(
            r'<h[1-6][^>]*>\s*(?:Product\s+[Dd]escription|From\s+the\s+[Mm]anufacturer)\s*</h[1-6]>',
            '', candidate, flags=re.IGNORECASE,
        )
        candidate = re.sub(
            r'^[ \t]*(?:Product\s+Description|From\s+the\s+Manufacturer)[ \t]*$',
            '', candidate, flags=re.MULTILINE | re.IGNORECASE,
        )

        text_only = html_module.unescape(re.sub(r'<[^>]+>', ' ', candidate)).strip()
        text_only = re.sub(r'\s+', ' ', text_only)
        if len(text_only) >= 100:
            if not re.match(
                r'^(?:Product\s+Specifications|Page\s+\d+\s+of\s+\d+|'
                r'age_range_description|brand_name)',
                text_only, re.IGNORECASE,
            ):
                text_chunk = candidate

    # STEP 2: #aplus_feature_div se SIRF IMAGES/VIDEOS
    aplus_images = []
    aplus_videos = []
    seen_img_urls = set()
    seen_vid_urls = set()

    m_aplus = re.search(
        rf'<div[^>]+id=["\']aplus_feature_div["\'][^>]*>(.*?){boundary}',
        html_doc, re.DOTALL | re.IGNORECASE,
    )
    if m_aplus:
        aplus_raw = m_aplus.group(1)
        aplus_raw = re.sub(r'<!--.*?-->', '', aplus_raw, flags=re.DOTALL)

        aplus_junk = (
            r'(?:sponsoredProducts|sp_detail|sponsored|ad-feedback|'
            r'similarities_feature_div|sims-consolidated|similar[-_]?brands|'
            r'comparison[-_]?table|product-comparison|aplus-comparison|'
            r'safety[-_]?documents|productSafety|safetyAndRegulatory|'
            r'legal[-_]?disclaimer|disclaimer|'
            r'aplusBrandStory|aplusSustainabilityStory|'
            r'aplus-module[^"\']*sponsored)'
        )
        for _ in range(3):
            aplus_raw = re.sub(
                rf'<(?:div|section|aside|ul|ol)[^>]*(?:id|class)=["\'][^"\']*{aplus_junk}[^"\']*["\'][^>]*>.*?</(?:div|section|aside|ul|ol)>',
                '', aplus_raw, flags=re.DOTALL | re.IGNORECASE,
            )

        for img_m in re.finditer(r'<img[^>]+>', aplus_raw, re.IGNORECASE):
            url = _extract_img_url(img_m.group(0))
            if not url:
                continue
            clean_url = url.split("?")[0]
            if clean_url in seen_img_urls:
                continue
            seen_img_urls.add(clean_url)
            alt_m = re.search(r'alt=["\']([^"\']*)["\']', img_m.group(0), re.I)
            alt = html_module.unescape(alt_m.group(1)) if alt_m else ""
            aplus_images.append({"url": url, "alt": alt})

        for v_m in re.finditer(r'<video[^>]*>.*?</video>', aplus_raw, re.DOTALL | re.IGNORECASE):
            v_tag = v_m.group(0)
            src_m = re.search(r'(?:src|data-video-url|data-src)=["\']([^"\']+)["\']', v_tag, re.I)
            if src_m:
                v_src = src_m.group(1).strip()
                if v_src.startswith("//"):
                    v_src = "https:" + v_src
                elif not v_src.startswith("http"):
                    v_src = "https://" + v_src
                if v_src not in seen_vid_urls:
                    seen_vid_urls.add(v_src)
                    aplus_videos.append(v_src)

        for v_m in re.finditer(r'data-video-url=["\']([^"\']+)["\']', aplus_raw, re.IGNORECASE):
            v_src = v_m.group(1).strip()
            if v_src.startswith("//"):
                v_src = "https:" + v_src
            elif not v_src.startswith("http"):
                v_src = "https://" + v_src
            if v_src not in seen_vid_urls:
                seen_vid_urls.add(v_src)
                aplus_videos.append(v_src)

    if not text_chunk and not aplus_images and not aplus_videos:
        return ""

    # STEP 3: Text cleanup
    if text_chunk:
        desc_chunk = text_chunk

        desc_chunk = re.sub(
            r'<(script|style|noscript|svg|button|form|input|iframe|link)[^>]*>.*?</\1>',
            '', desc_chunk, flags=re.DOTALL | re.IGNORECASE,
        )
        desc_chunk = re.sub(r'<(?:link|input)[^>]*>', '', desc_chunk, flags=re.IGNORECASE)

        desc_chunk = re.sub(r'<!--.*?-->', '', desc_chunk, flags=re.DOTALL)
        desc_chunk = re.sub(r'!-{2,}[^\n]*', '', desc_chunk)

        desc_chunk = re.sub(r'/?\w+\s*&gt;', ' ', desc_chunk)
        desc_chunk = re.sub(r'/?\w+\s*&lt;', ' ', desc_chunk)

        def _clean_table(match):
            table = match.group(0)
            if re.search(r'<(?:img|video)\b', table, re.IGNORECASE):
                return re.sub(
                    r'</?(?:table|thead|tbody|tfoot|tr|td|th|colgroup|col|caption)\b[^>]*>',
                    '', table, flags=re.IGNORECASE,
                )
            return ""
        desc_chunk = re.sub(r'<table[^>]*>.*?</table>', _clean_table, desc_chunk, flags=re.DOTALL | re.IGNORECASE)

        desc_chunk = re.sub(
            r'(?:[a-zA-Z][\w-]*\s*=\s*["\'][^"\']*["\']\s*){3,}',
            '', desc_chunk, flags=re.IGNORECASE,
        )
        desc_chunk = re.sub(
            r'\b(?:data-[\w-]+|id|class|style|role|aria-[\w-]+)\s*=\s*["\'][^"\']*["\']',
            '', desc_chunk, flags=re.IGNORECASE,
        )

        js_patterns = [
            r'var\s+\w+\s*=\s*[^;]{1,300};',
            r'function\s+\w*\s*\([^)]*\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            r'\bif\s*\([^)]{1,200}\)\s*\{[^{}]*\}',
            r'A\.\$\.ajax\s*\([^{}]*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*\)',
            r'\breturn\s+[^;]{1,200};',
            r'\b(?:const|let)\s+\w+\s*=\s*[^;]{1,200};',
            r'\bdocument\.\w+\([^)]*\)',
            r'\bwindow\.\w+(?:\.\w+)*',
            r'DESKTOP_METRIC_PREFIX[^;]{0,200};',
            r'P\.log\s*\([^)]*\)',
            r'JSON\.(?:parse|stringify)\s*\([^)]*\)',
        ]
        for js_pat in js_patterns:
            desc_chunk = re.sub(js_pat, '', desc_chunk, flags=re.IGNORECASE)

        desc_chunk = re.sub(r"^\s*['\"]\s*;\s*", '', desc_chunk, flags=re.MULTILINE)
        desc_chunk = re.sub(r'\}\)\s*;\s*\}\)\)\s*;', '', desc_chunk)
        desc_chunk = re.sub(r'\}\s*\)\s*;', '', desc_chunk)

        desc_chunk = re.sub(
            r"(?:Amazon['\u2019]?s\s+Choice\s*)?"
            r"\$?\d[\d,.]*\s*\$?\d[\d,.]*"
            r"(?:\s*\([^)]*\))?"
            r"(?:\s*-\d+%)?"
            r"(?:\s*FREE\s+delivery[^<\n]*)?",
            '', desc_chunk, flags=re.IGNORECASE,
        )
        desc_chunk = re.sub(r"Amazon['\u2019]?s\s+Choice[^\n<]*", '', desc_chunk, flags=re.IGNORECASE)
        desc_chunk = re.sub(r'Climate\s+Pledge\s+Friendly[^\n<]*', '', desc_chunk, flags=re.IGNORECASE)
        desc_chunk = re.sub(r'FREE\s+delivery[^\n<]*', '', desc_chunk, flags=re.IGNORECASE)

        has_video = bool(re.search(r'<(?:video|source)\b', desc_chunk, re.IGNORECASE))
        junk_text = (
            r'Similar\s+brands\s+on\s+Amazon[^\n<]*|'
            r'Safety\s+and\s+product\s+resources[^\n<]*|'
            r'Safety\s+Tips[^\n<]*|'
            r'Safety\s+documents[^\n<]*|'
            r'CHOKING\s+HAZARD[^\n<]*|'
            r'Not\s+for\s+children\s+under\s+\d+\s+years[^\n<]*|'
            r'\d*\s*K\+\s+(?:customers|orders)[^\n<]*|'
            r'100K\+\s+(?:orders|customers)[^\n<]*|'
            r'Top\s+Brand\s*:\s*[^\n<]*|'
            r'Brands\s+in\s+this\s+category\s+on\s+Amazon[^\n<]*|'
            r'Sponsored[^\n<]*|'
            r'Shop\s+[A-Za-z0-9][^\n<]*|'
            r'Not\s+Suitable\s+for\s+Children[^\n<]*|'
            r'Legal\s+Disclaimer[^\n<]*|'
            r'User\s+Manual\s*\(PDF\)[^\n<]*|'
            r'WARNING\s*:\s*[^\n<]*|'
            r'Highly\s+Rated[^\n<]*|'
            r'Trending[^\n<]*|'
            r'Low\s+Returns[^\n<]*|'
            r'Customers\s+usually\s+keep[^\n<]*|'
            r'Buying\s+Options[^\n<]*|'
            r'Customer\s+Reviews[^\n<]*|'
            r'Page\s+\d+\s+of\s+\d+[^\n<]*|'
            r'From\s+the\s+brand[^\n<]*|'
            r'Leave\s+feedback[^\n<]*|'
            r'Trusted\s+by\s+Families\s+Worldwide[^\n<]*|'
            r'Battle\s+Hooks[^\n<]*|'
            r'Make\s+family\s+time\s+more\s+fun[^\n<]*|'
            r'Incredibly\s+Fun\s+Card\s+Games[^\n<]*'
        )
        if not has_video:
            junk_text += r'|Product\s+Videos[^\n<]*'
        desc_chunk = re.sub(junk_text, '', desc_chunk, flags=re.IGNORECASE)

        desc_chunk = re.sub(
            r'Product\s+Specifications.*?(?=<\s*h[1-6]\b|$)',
            '', desc_chunk, flags=re.IGNORECASE | re.DOTALL,
        )
        desc_chunk = re.sub(r'^[a-z_]{3,40}\t[^\n]*$', '', desc_chunk, flags=re.MULTILINE)
        desc_chunk = re.sub(
            r'^[ \t]*Product\s+Description[ \t]*$',
            '', desc_chunk, flags=re.MULTILINE | re.IGNORECASE,
        )
        desc_chunk = re.sub(r'\bPage\s+\d+\s+of\s+\d+\b[^\n<]*', '', desc_chunk, flags=re.IGNORECASE)

        desc_chunk = re.sub(
            r'<h[1-6][^>]*>\s*(?:Important\s+information|Safety\s+Information|'
            r'Directions|Warnings?|Legal\s+Disclaimer)\s*</h[1-6]>',
            '', desc_chunk, flags=re.IGNORECASE,
        )

        desc_chunk = re.sub(
            r'(?:\u0e04\u0e33\u0e40\u0e15\u0e37\u0e2d\u0e19|\u8b66\u544a|\u8b66\u544a\uff1a)[^\n<]*',
            '', desc_chunk, flags=re.IGNORECASE,
        )

        desc_chunk = re.sub(
            r'\b1\.\s+Set\s+up\s+the\s+game\s+board.*?(?=\n\n|<\s*h[1-6]|<\s*p\b|$)',
            '', desc_chunk, flags=re.IGNORECASE | re.DOTALL,
        )
        desc_chunk = re.sub(
            r'\b\d\.\s+[^.]{5,200}\.\s*\d\.\s+[^.]{5,200}\.\s*\d\.\s+[^.]{5,200}\.\s*\d\.\s+[^.]{5,200}\.',
            '', desc_chunk, flags=re.IGNORECASE | re.DOTALL,
        )

        def _clean_img(match):
            url = _extract_img_url(match.group(0))
            if not url:
                return ""
            clean_url = url.split("?")[0]
            if clean_url in seen_img_urls:
                return ""
            seen_img_urls.add(clean_url)
            alt_m = re.search(r'alt=["\']([^"\']*)["\']', match.group(0), re.I)
            alt = html_module.unescape(alt_m.group(1)) if alt_m else ""
            return (
                f'<img src="{_escape(url)}" alt="{_escape(alt)}" '
                f'style="max-width: 100%; height: auto; display: block; '
                f'margin: 16px auto; border-radius: 4px;" />'
            )
        desc_chunk = re.sub(r'<img[^>]+>', _clean_img, desc_chunk, flags=re.IGNORECASE)

        def _clean_video(match):
            v_tag = match.group(0)
            src_m = re.search(r'(?:src|data-video-url|data-src)=["\']([^"\']+)["\']', v_tag, re.I)
            v_src = src_m.group(1) if src_m else ""
            if v_src:
                if v_src.startswith("//"):
                    v_src = "https:" + v_src
                elif not v_src.startswith("http"):
                    v_src = "https://" + v_src
                return (
                    f'<div style="margin: 16px auto; max-width: 100%;">'
                    f'<video controls style="max-width: 100%; height: auto; display: block; '
                    f'margin: 0 auto; border-radius: 6px;">'
                    f'<source src="{v_src}" type="video/mp4" />'
                    f'Your browser does not support the video tag.</video></div>'
                )
            return ""
        desc_chunk = re.sub(
            r'<video[^>]*>.*?</video>', _clean_video,
            desc_chunk, flags=re.DOTALL | re.IGNORECASE,
        )

        desc_chunk = re.sub(
            r'<h[1-3]\b[^>]*>',
            '<h4 style="margin: 16px 0 8px 0; font-weight: bold; color: #222;">',
            desc_chunk, flags=re.IGNORECASE,
        )
        desc_chunk = re.sub(r'</h[1-3]>', '</h4>', desc_chunk, flags=re.IGNORECASE)

        desc_chunk = re.sub(r'</?(?:ol|ul|li)\b[^>]*>', '', desc_chunk, flags=re.IGNORECASE)
        desc_chunk = re.sub(
            r'</?(?:div|span|section|article|header|footer|nav|a|i|b|strong|em)\b[^>]*>',
            '', desc_chunk, flags=re.IGNORECASE,
        )

        desc_chunk = html_module.unescape(desc_chunk)

        desc_chunk = re.sub(r'/?\w+>', ' ', desc_chunk)
        desc_chunk = re.sub(r'/?\w+<', ' ', desc_chunk)
        desc_chunk = re.sub(r'(?<=\s)[<>](?=\s)', ' ', desc_chunk)
        desc_chunk = re.sub(r'(?<=\s)[<>]$', '', desc_chunk, flags=re.MULTILINE)
        desc_chunk = re.sub(r'^[<>](?=\s)', '', desc_chunk, flags=re.MULTILINE)

        desc_chunk = re.sub(r'\b\w[\w-]*\s*=\s*["\'][^"\']{1,200}["\']', '', desc_chunk)
        desc_chunk = re.sub(r'\b(?:A\.\$\.|A\.on\(|P\.log\()', '', desc_chunk)
        desc_chunk = re.sub(r'^\s*[;]+\s*', '', desc_chunk, flags=re.MULTILINE)
        desc_chunk = re.sub(r'\{\s*\}', '', desc_chunk)
        desc_chunk = re.sub(r'\[\s*\]', '', desc_chunk)

        for _ in range(3):
            desc_chunk = re.sub(r'<(p|h[1-6])[^>]*>\s*</\1>', '', desc_chunk, flags=re.IGNORECASE)
        desc_chunk = re.sub(r'\n\s*\n+', '\n\n', desc_chunk)
        lines = [line.strip() for line in desc_chunk.split('\n') if line.strip()]
        desc_chunk = '\n\n'.join(lines)

        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', desc_chunk) if p.strip()]
        seen_signatures = set()
        deduped = []
        for para in paragraphs:
            plain = re.sub(r'<[^>]+>', '', para).strip().lower()
            plain = re.sub(r'\s+', ' ', plain)
            sig = plain[:120]
            if sig and sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            deduped.append(para)
        desc_chunk = '\n\n'.join(deduped)
    else:
        desc_chunk = ""

    # STEP 4: A+ media append
    media_parts = []

    for v_src in aplus_videos:
        media_parts.append(
            f'<div style="margin: 16px auto; max-width: 100%;">'
            f'<video controls style="max-width: 100%; height: auto; display: block; '
            f'margin: 0 auto; border-radius: 6px;">'
            f'<source src="{_escape(v_src)}" type="video/mp4" />'
            f'Your browser does not support the video tag.</video></div>'
        )

    for img in aplus_images:
        media_parts.append(
            f'<img src="{_escape(img["url"])}" alt="{_escape(img["alt"])}" '
            f'style="max-width: 100%; height: auto; display: block; '
            f'margin: 16px auto; border-radius: 4px;" />'
        )

    if media_parts:
        media_html = '\n'.join(media_parts)
        desc_chunk = (desc_chunk + '\n\n' + media_html) if desc_chunk else media_html

    # STEP 5: Final safety net
    junk_signatures = [
        "var HEADER_STRING", "A.$.ajax", "data-csa-c-", "modalInstance",
        "serializedPayload", "generatePayload", "DESKTOP_METRIC_PREFIX",
        "CardsClient", "show up to", "/p&gt;", "/h4&gt;", "/p>", "/h4>",
        "&gt;", "&lt;",
    ]
    if any(sig in desc_chunk for sig in junk_signatures):
        logger.warning(
            f"Junk residue detected; dropping text, keeping media only. "
            f"Residue: {[s for s in junk_signatures if s in desc_chunk]}"
        )
        desc_chunk = '\n'.join(media_parts) if media_parts else ""

    desc_chunk = re.sub(r'<!--.*?-->', '', desc_chunk, flags=re.DOTALL)
    desc_chunk = re.sub(r'!-{2,}[^\n]*', '', desc_chunk)

    desc_chunk = re.sub(r'/?\w+\s*&gt;', ' ', desc_chunk)
    desc_chunk = re.sub(r'/?\w+\s*&lt;', ' ', desc_chunk)
    desc_chunk = re.sub(r'/?\w+>', ' ', desc_chunk)
    desc_chunk = re.sub(r'/?\w+<', ' ', desc_chunk)

    return desc_chunk.strip()