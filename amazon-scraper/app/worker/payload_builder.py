# app/worker/payload_builder.py

def build_shopify_payload(main_data: dict, final_price: float, final_tags: list, extracted_categories: list, parent_in_stock: bool, parent_stock: int) -> dict:
    return {
        "title":        main_data.get("title"),
        "description":  main_data.get("description", ""),
        "bullets":      main_data.get("bullets") or [],
        "size_chart":   main_data.get("size_chart") or "",
        "reviews":      main_data.get("reviews") or [],
        "brand":        main_data.get("brand"),
        "images":       main_data.get("images") or [],
        "price":        final_price,
        "tags":         final_tags,  # ✅ Tags yahan se jate hain
        "categories":   extracted_categories, 
        "product_type": extracted_categories[-1] if extracted_categories else "General", # ✅ Category yahan se jati hai
        "asin":         main_data.get("asin"),
        "details":      main_data.get("details") or {},
        "is_available": parent_in_stock,
        "in_stock":     parent_in_stock,
        "stock_qty":    parent_stock,
    }