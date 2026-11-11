def _calculate_price(price: float, markup_val: float, markup_type: str, extra_percent: float, tax_rate: float) -> float:
    price = float(price or 0.0)
    markup_val = float(markup_val or 0.0)
    extra_percent = float(extra_percent or 0.0)
    tax_rate = float(tax_rate or 0.0)

    if markup_val == 0.0 and extra_percent == 0.0 and tax_rate == 0.0:
        return round(price, 2)

    if markup_type == "percent":
        base = price + (price * (markup_val / 100.0))
    elif markup_type == "both":
        base = (price + markup_val) + ((price + markup_val) * (extra_percent / 100.0))
    else:  # fixed
        base = price + markup_val
        if extra_percent > 0:
            base = base + (base * (extra_percent / 100.0))

    if tax_rate > 0:
        base = base + (base * (tax_rate / 100.0))

    return round(base, 2)