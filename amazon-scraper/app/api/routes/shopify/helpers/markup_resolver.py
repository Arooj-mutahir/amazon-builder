from app.models import ShopifyStore

def _resolve_markup(store: ShopifyStore, markup, markup_type, extra_percent, tax_rate) -> tuple:
    def _clean(val):
        if val is None:
            return None
        try:
            f = float(val)
            return 0.0 if (f != f or f < 0) else f
        except (ValueError, TypeError):
            return None

    clean_markup = _clean(markup)
    clean_extra = _clean(extra_percent)
    clean_tax = _clean(tax_rate)
    clean_type = str(markup_type).strip().lower() if markup_type else None

    if clean_markup is None:
        clean_markup = _clean(store.default_markup) or 0.0
    
    if clean_extra is None:
        clean_extra = _clean(store.default_extra_percent) or 0.0
        
    if clean_tax is None:
        clean_tax = _clean(store.default_tax_rate) or 0.0
        
    if not clean_type or clean_type not in ("fixed", "percent", "both"):
        clean_type = str(store.default_markup_type or "fixed").strip().lower()

    return clean_markup, clean_type, clean_extra, clean_tax