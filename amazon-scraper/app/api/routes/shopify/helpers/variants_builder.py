def _derive_dimensions(main_data: dict) -> list:
    dims_order = []
    dims_values = {}
    for vp in main_data.get("variant_products") or []:
        for ov in vp.get("option_values") or []:
            name = (ov.get("name") or "").strip()
            value = (ov.get("value") or "").strip()
            if not name or not value: continue
            if name not in dims_values:
                dims_order.append(name)
                dims_values[name] = []
            if value not in dims_values[name]: dims_values[name].append(value)
    if not dims_order:
        attr = main_data.get("variant_attributes") or []
        if attr:
            name = (attr[0].get("name") or "Style").strip()
            dims_order.append(name)
            dims_values[name] = []
            for a in attr:
                val = (a.get("value") or "").strip()
                if val and val not in dims_values[name]: dims_values[name].append(val)
    return [(n, dims_values[n]) for n in dims_order]


def _build_clean_variants(main_data: dict, fetched_variants: list, default_option_name: str = "Style") -> list:
    asin_meta = {}
    
    for vp in main_data.get("variant_products") or []:
        a = vp.get("asin")
        if not a: continue
        asin_meta[a] = {
            "images": vp.get("images") or [],
            "option_values": vp.get("option_values") or [], 
            "price": None,
            "in_stock": vp.get("in_stock"),
            "stock_qty": vp.get("stock_qty"),
        }
        
    for v in fetched_variants:
        a = v.get("asin")
        if not a: continue
        entry = asin_meta.setdefault(a, {
            "images": [], "option_values": [], "price": None,
            "in_stock": None, "stock_qty": None,
        })
        if not entry.get("images") and v.get("images"): entry["images"] = v["images"]
        if v.get("price") is not None: entry["price"] = v["price"]
        if v.get("option_values") and not entry.get("option_values"): entry["option_values"] = v["option_values"]
        if v.get("in_stock") is not None: entry["in_stock"] = v["in_stock"]
        if v.get("stock_qty") is not None: entry["stock_qty"] = v["stock_qty"]
    
    dimensions = _derive_dimensions(main_data)
    if not dimensions: dimensions = [(default_option_name, [])]

    clean = []
    seen_labels = set()
    
    for vp in main_data.get("variant_products") or []:
        v_asin = vp.get("asin")
        if not v_asin: continue
        meta = asin_meta.get(v_asin) or {}
        opts = meta.get("option_values") or vp.get("option_values") or []
        option_values, label_parts = [], []
        for dim_name, _ in dimensions:
            matching_val = next((ov.get("value") for ov in opts if (ov.get("name") or "").strip() == dim_name and ov.get("value")), None)
            if matching_val:
                option_values.append({"name": dim_name, "value": str(matching_val)})
                label_parts.append(str(matching_val))
        for ov in opts:
            n = (ov.get("name") or "").strip()
            v = (ov.get("value") or "").strip()
            if n and v and not any(o["name"] == n for o in option_values):
                option_values.append({"name": n, "value": v})
                label_parts.append(v)
        if not option_values:
            option_values = [{"name": default_option_name, "value": v_asin}]
            label_parts = [v_asin]
            
        label = " / ".join(p for p in label_parts if p)
        sig = tuple((o["name"], o["value"]) for o in option_values)
        counter = 2
        while sig in seen_labels:
            last = option_values[-1]
            last["value"] = f"{last['value']} ({v_asin[-4:]}-{counter})"
            sig = tuple((o["name"], o["value"]) for o in option_values)
            counter += 1
        seen_labels.add(sig)
        
        child_images = meta.get("images") or []
        if not child_images and vp.get("images"): child_images = vp["images"]
        if not child_images and main_data.get("images"): child_images = [main_data["images"][0]]
        
        child_price = meta.get("price")
        if child_price is None: child_price = main_data.get("price") or 0.0
        
        child_in_stock = meta.get("in_stock")
        if child_in_stock is None: child_in_stock = vp.get("in_stock")
        
        child_stock_qty = meta.get("stock_qty")
        if child_stock_qty is None: child_stock_qty = vp.get("stock_qty")
        
        clean.append({
            "asin": v_asin, 
            "option_values": option_values, 
            "price": child_price, 
            "images": child_images,
            "title": (vp.get("attributes") or {}).get("Title") or label,
            "in_stock": child_in_stock, 
            "stock_qty": child_stock_qty, 
        })
    return clean