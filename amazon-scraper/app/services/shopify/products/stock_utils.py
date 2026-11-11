def _variant_stock(v_raw: dict, default_stock_qty: int = 0) -> tuple:
    in_stock = v_raw.get("is_available")
    if in_stock is None:
        in_stock = v_raw.get("in_stock")
    if in_stock is None:
        return None, None
    qty = v_raw.get("stock_qty")
    if qty is None:
        qty = default_stock_qty if in_stock else 0
    return bool(in_stock), int(qty)

def _resolve_parent_stock(product_data: dict, default_stock_qty: int = 0) -> int:
    available = product_data.get("is_available")
    if available is None:
        available = product_data.get("in_stock", False)

    stock_qty = product_data.get("stock_qty")

    if not available:
        return 0
    if stock_qty is None:
        return default_stock_qty
    try:
        return int(stock_qty)
    except (TypeError, ValueError):
        return default_stock_qty