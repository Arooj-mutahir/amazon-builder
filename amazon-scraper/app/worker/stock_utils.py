# app/worker/stock_utils.py

def _get_availability(v_raw: dict):
    val = v_raw.get("is_available")
    if val is None:
        val = v_raw.get("in_stock")
    return val


def _resolve_stock(available, stock_qty, default_stock_qty: int = 0) -> int | None:
    if available is None:
        return None
    if not available:
        return 0
    if stock_qty is None:
        return int(default_stock_qty)
    try:
        return int(stock_qty)
    except (TypeError, ValueError):
        return int(default_stock_qty)