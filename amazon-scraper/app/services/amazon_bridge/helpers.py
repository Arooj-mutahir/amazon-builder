def _img_url(img):
    return (img.get("link") or img.get("large") or img.get("thumbnail")) if isinstance(img, dict) else None

def _norm(val):
    return str(val or "").lower().strip()

def _brand_name(raw_brand):
    return raw_brand.get("name") if isinstance(raw_brand, dict) else str(raw_brand or "")

def _price_amount(raw_price):
    if not raw_price:
        return 0.0
    if isinstance(raw_price, dict):
        try:
            return float(raw_price.get("amount") or 0)
        except Exception:
            return 0.0
    try:
        return float(raw_price)
    except Exception:
        return 0.0

def _rating_avg(raw_rating):
    if isinstance(raw_rating, dict):
        try:
            return float(raw_rating.get("average") or 0)
        except Exception:
            return 0.0
    return 0.0

def _rating_count(raw_rating):
    if isinstance(raw_rating, dict):
        try:
            return int(raw_rating.get("count") or 0)
        except Exception:
            return 0
    return 0