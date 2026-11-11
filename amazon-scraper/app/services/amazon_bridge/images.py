# app/services/amazon_bridge/images.py
import re
import json

def extract_all_gallery_images(html_str: str) -> list:
    if not html_str:
        return []
    images = []
    seen = set()

    def _add(url):
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if url.startswith("//"):
            url = "https:" + url
        elif not url.startswith("http"):
            url = "https://" + url
        if url not in seen and not any(bad in url for bad in [
            "grey-pixel", "pixel.gif", "transparent-pixel", "data:image",
        ]):
            seen.add(url)
            images.append(url)

    patterns = [
        r"['\"]colorImages['\"]\s*:\s*\{\s*['\"]initial['\"]\s*:\s*"
        r"(?:A\.\$\.parseJSON\(|JSON\.parse\()?['\"](\[.+?\])['\"]",
        r"['\"]initial['\"]\s*:\s*(?:A\.\$\.parseJSON\(|JSON\.parse\()?['\"](\[.+?\])['\"]",
        r"parseJSON\('(\[\s*\{.*?\"hiRes\".*?\}\s*\])'\)",
    ]
    for p in patterns:
        m = re.search(p, html_str)
        if m:
            raw = m.group(1).replace("\\'", "'").replace('\\"', '"').replace('\\\\', '\\')
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            _add(item.get("hiRes") or item.get("large") or item.get("mainUrl"))
                    if images:
                        break
            except Exception:
                pass

    if not images:
        m = re.search(r'["\']colorImages["\']\s*:\s*(\{.+?\})\s*,\s*["\']', html_str)
        if m:
            try:
                data = json.loads(m.group(1))
                initial = data.get("initial", [])
                if isinstance(initial, list):
                    for item in initial:
                        if isinstance(item, dict):
                            _add(item.get("hiRes") or item.get("large"))
            except Exception:
                pass

    if not images:
        m = re.search(
            r'data-a-state=\'{"key":"desktop-magic-block-image-viewer"}\'>(.*?)</script>',
            html_str,
        )
        if m:
            try:
                data = json.loads(m.group(1))
                for item in data.get("images", []):
                    if isinstance(item, dict):
                        _add(item.get("hiRes") or item.get("large"))
            except Exception:
                pass

    if not images:
        m = re.search(r'imageGalleryData["\']?\s*:\s*(\[.+?\])', html_str)
        if m:
            try:
                data = json.loads(m.group(1))
                for item in data:
                    if isinstance(item, dict):
                        _add(item.get("mainUrl") or item.get("hiRes") or item.get("large"))
            except Exception:
                pass

    if not images:
        m = re.search(
            r'id=["\']landingImage["\'][^>]*\sdata-old-hires=["\']([^"\']+)["\']',
            html_str,
        ) or re.search(
            r'id=["\']landingImage["\'][^>]*\ssrc=["\']([^"\']+)["\']',
            html_str,
        )
        if m:
            _add(m.group(1))

    return images


def extract_color_images_map(html_str: str) -> dict:
    result = {}
    if not html_str:
        return result

    m = re.search(r'["\']colorImages["\']\s*:\s*(\{.+?\})\s*,\s*["\']', html_str)
    if not m:
        m = re.search(r'data\[["\']colorImages["\']\]\s*=\s*(\{.+?\});', html_str)

    if m:
        try:
            data = json.loads(m.group(1))
            for key, val in data.items():
                if key == "initial":
                    continue
                if isinstance(val, list):
                    urls = []
                    for item in val:
                        if isinstance(item, dict):
                            u = item.get("hiRes") or item.get("large")
                            if u:
                                urls.append(u)
                    if urls:
                        result[_norm(key)] = urls
        except Exception:
            pass
    return result