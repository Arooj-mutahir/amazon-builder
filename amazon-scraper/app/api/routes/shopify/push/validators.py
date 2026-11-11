VALID_MARKUP_TYPES = {"fixed", "percent", "both"}

def clean_markup_values(markup, markup_type, extra_percent, tax_rate):
    # ✅ Force strict values
    m = float(markup) if markup is not None else 0.0
    m_type = (markup_type or "fixed").lower()
    e = float(extra_percent) if extra_percent is not None else 0.0
    t = float(tax_rate) if tax_rate is not None else 0.0

    # ✅ FIX: Agar "both" nahi hai, toh Extra ko forcefully 0 karein
    if m_type != "both":
        e = 0.0
        
    return m, m_type, e, t