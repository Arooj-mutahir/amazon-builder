import re

def extract_asin_from_url(url: str) -> str:
    patterns = [r"/dp/([A-Z0-9]{10})", r"/gp/product/([A-Z0-9]{10})", r"/product/([A-Z0-9]{10})", r"/ASIN/([A-Z0-9]{10})"]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
    return None

def _normalize_amazon_url(url: str) -> str:
    if not url or not isinstance(url, str): return url
    url = url.strip()
    if not url: return url
    if not url.startswith(("http://", "https://")): url = "https://" + url
    if "amazon." in url and "www.amazon." not in url: url = url.replace("amazon.", "www.amazon.", 1)
    asin = extract_asin_from_url(url)
    return f"https://www.amazon.com/dp/{asin}" if asin else url