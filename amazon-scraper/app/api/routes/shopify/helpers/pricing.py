def calculate_final_price(amazon_price, markup, markup_type, extra_percent=0.0, tax_rate=0.0):
    if amazon_price is None:
        return 0.0
    try:
        amazon_price = float(amazon_price)
    except (TypeError, ValueError):
        return 0.0

    markup = float(markup) if markup is not None else 0.0
    extra_percent = float(extra_percent) if extra_percent is not None else 0.0
    tax_rate = float(tax_rate) if tax_rate is not None else 0.0
    markup_type = str(markup_type or "fixed").strip().lower()

    if markup == 0.0 and extra_percent == 0.0 and tax_rate == 0.0:
        return round(amazon_price, 2)

    # 1. Base Price
    if markup_type == "percent":
        base_price = amazon_price + (amazon_price * (markup / 100.0))
    elif markup_type == "both":
        base_price = (amazon_price + markup) + ((amazon_price + markup) * (extra_percent / 100.0))
    else:  # fixed
        base_price = amazon_price + markup

    # 2. Tax
    if tax_rate > 0.0:
        final_price = base_price + (base_price * (tax_rate / 100.0))
    else:
        final_price = base_price

    return round(final_price, 2)