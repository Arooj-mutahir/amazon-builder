# app/services/amazon_bridge/reviews.py
import re
import html as html_module

def extract_top_reviews(html_doc: str, limit: int = 15, fallback_reviews: list = None) -> list:
    if not html_doc:
        return []

    reviews = []

    tag_matches = list(re.finditer(
        r'<(?:div|li)[^>]+(?:data-hook=["\'](?:review|review-card)["\']|'
        r'id=["\']customer_review-[A-Z0-9]+["\'])[^>]*>',
        html_doc, re.IGNORECASE,
    ))
    cards = []
    if tag_matches:
        for i in range(len(tag_matches)):
            start_idx = tag_matches[i].start()
            end_idx = tag_matches[i + 1].start() if i + 1 < len(tag_matches) else len(html_doc)
            if end_idx - start_idx > 25000:
                end_idx = start_idx + 25000
            cards.append(html_doc[start_idx:end_idx])

    for card in cards[:limit]:
        author = "Amazon Customer"
        m_author = re.search(
            r'class=["\'][^"\']*a-profile-name[^"\']*["\'][^>]*>(.*?)</(?:span|div)>',
            card, re.IGNORECASE,
        )
        if not m_author:
            m_author = re.search(
                r'class=["\'][^"\']*a-profile-name[^"\']*["\'][^>]*>([^<\r\n]+)',
                card, re.IGNORECASE,
            )
        if m_author:
            name = re.sub(r'<[^>]+>', '', m_author.group(1)).strip()
            if name:
                author = html_module.unescape(name)

        rating = 5.0
        m_rating = re.search(
            r'data-hook=["\'](?:review-star-rating|cmps-review-star-rating)["\'][^>]*>'
            r'.*?<span[^>]*class=["\'][^"\']*a-icon-alt[^"\']*["\'][^>]*>([^<]+)</span>',
            card, re.DOTALL | re.IGNORECASE,
        )
        if not m_rating:
            m_rating = re.search(
                r'<i[^>]*class=["\'][^"\']*(?:review-rating|a-icon-star)[^"\']*["\'][^>]*>'
                r'.*?<span[^>]*class=["\'][^"\']*a-icon-alt[^"\']*["\'][^>]*>([^<]+)</span>',
                card, re.DOTALL | re.IGNORECASE,
            )
        if m_rating:
            num_m = re.search(r'([0-9]+(?:\.[0-9]+)?)', m_rating.group(1))
            if num_m:
                try:
                    rating = float(num_m.group(1))
                except ValueError:
                    pass

        title = ""
        m_title = re.search(
            r'data-hook=["\'](?:reviewTitle|review-title)["\'][^>]*>(.*?)</(?:a|span|h5|div)>',
            card, re.DOTALL | re.IGNORECASE,
        )
        if not m_title:
            m_title = re.search(
                r'class=["\'][^"\']*(?:review-title|reviewTitle)[^"\']*["\'][^>]*>(.*?)</(?:a|span|h5|div)>',
                card, re.DOTALL | re.IGNORECASE,
            )
        if m_title:
            raw_title = m_title.group(1)
            clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
            clean_title = re.sub(
                r'^[0-9]+(?:\.[0-9]+)?\s*out of 5 stars\s*', '',
                clean_title, flags=re.IGNORECASE,
            )
            title = html_module.unescape(clean_title)

        text = ""
        m_body = re.search(
            r'data-hook=["\']reviewRichContentContainer["\'][^>]*>(.*?)'
            r'(?=<div[^>]+data-hook=["\'](?:review-date|review-by-line|helpful-vote|format-strip)|'
            r'</div>\s*</div>\s*</div>|$)',
            card, re.DOTALL | re.IGNORECASE,
        )
        if not m_body:
            m_body = re.search(
                r'data-hook=["\'](?:review-body|review-collapsed)["\'][^>]*>(.*?)</(?:span|div)>',
                card, re.DOTALL | re.IGNORECASE,
            )
        if not m_body:
            m_body = re.search(
                r'data-hook=["\']reviewText["\'][^>]*>(.*?)'
                r'(?=<div[^>]+data-hook=["\'](?:review-date|review-by-line|helpful-vote)|'
                r'<div class=["\'][^"\']*a-row|$)',
                card, re.DOTALL | re.IGNORECASE,
            )
        if not m_body:
            m_body = re.search(
                r'class=["\'][^"\']*review-text(?:-content)?[^"\']*["\'][^>]*>(.*?)</(?:span|div)>',
                card, re.DOTALL | re.IGNORECASE,
            )
        if m_body:
            body_raw = m_body.group(1)
            body_raw = re.sub(r'<br\s*/?>', '\n', body_raw, flags=re.IGNORECASE)
            body_raw = re.sub(r'</p>', '\n', body_raw, flags=re.IGNORECASE)
            clean_text = re.sub(r'<[^>]+>', ' ', body_raw)
            clean_text = re.sub(
                r'(?:Brief|Full)\s*content\s*visible,?\s*double\s*tap\s*to\s*read\s*'
                r'(?:full|brief)\s*content\.?',
                '', clean_text, flags=re.IGNORECASE,
            )
            clean_text = html_module.unescape(clean_text)
            text = re.sub(r'\s+', ' ', clean_text).strip()

        verified = bool(re.search(
            r'data-hook=["\'](?:avp-badge|avp-badge-linkless)["\']|Verified Purchase',
            card, re.IGNORECASE,
        ))

        images = []
        seen_imgs = set()
        for img_m in re.finditer(
            r'<img[^>]+(?:data-hook=["\']review-image-tile["\']|'
            r'class=["\'][^"\']*review-image(?:-tile)?[^"\']*["\']|'
            r'alt=["\']Customer image["\'])[^>]*>',
            card, re.IGNORECASE,
        ):
            src_m = re.search(
                r'(?:src|data-src|data-old-hires|data-a-hires)=["\']([^"\']+)["\']',
                img_m.group(0), re.IGNORECASE,
            )
            if src_m:
                u = src_m.group(1).strip()
                if not any(bad in u.lower() for bad in [
                    "grey-pixel", "pixel.gif", "transparent-pixel", "data:image",
                ]):
                    if u.startswith("//"):
                        u = "https:" + u
                    elif not u.startswith("http"):
                        u = "https://" + u
                    full_u = re.sub(
                        r'\._[A-Za-z0-9_,-]+(?=\.[a-zA-Z]+$)', '',
                        u, flags=re.IGNORECASE,
                    )
                    if full_u not in seen_imgs:
                        seen_imgs.add(full_u)
                        images.append(full_u)

        videos = []
        seen_vids = set()
        for v_m in re.finditer(
            r'<(?:video|source)[^>]+src=["\']([^"\']+)["\']',
            card, re.IGNORECASE,
        ):
            v_url = v_m.group(1).strip()
            if v_url.startswith("//"):
                v_url = "https:" + v_url
            elif not v_url.startswith("http"):
                v_url = "https://" + v_url
            if v_url not in seen_vids:
                seen_vids.add(v_url)
                videos.append(v_url)

        for v_m in re.finditer(
            r'data-video(?:-url|-mp4)?=["\']([^"\']+)["\']',
            card, re.IGNORECASE,
        ):
            v_url = v_m.group(1).strip()
            if v_url.startswith("//"):
                v_url = "https:" + v_url
            elif not v_url.startswith("http"):
                v_url = "https://" + v_url
            if v_url not in seen_vids:
                seen_vids.add(v_url)
                videos.append(v_url)

        reviews.append({
            "author": author,
            "name": author,
            "rating": rating,
            "title": title,
            "text": text,
            "images": images,
            "videos": videos,
            "verified": verified,
            "is_verified_purchase": verified,
        })

    if not reviews and fallback_reviews:
        for fr in fallback_reviews[:limit]:
            author_data = fr.get("author") or {}
            author_str = author_data.get("name") if isinstance(author_data, dict) else str(author_data or "Amazon Customer")
            reviews.append({
                "author": author_str or "Amazon Customer",
                "rating": float(fr.get("rating") or 5.0),
                "title": fr.get("title") or "",
                "text": fr.get("text") or "",
                "images": fr.get("images") or [],
                "videos": fr.get("videos") or [],
                "verified": bool(fr.get("is_verified_purchase")),
            })

    return reviews[:limit]