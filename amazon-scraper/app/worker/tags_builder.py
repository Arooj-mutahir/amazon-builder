# app/worker/tags_builder.py

def build_final_tags(main_data: dict) -> tuple[list, list]:
    extracted_categories = main_data.get("tags") or []
    final_tags = []
    
    for cat in extracted_categories:
        if ">" in cat:
            parts = [p.strip() for p in cat.split(">")]
            final_tags.extend(parts)
        else:
            if cat.strip(): 
                final_tags.append(cat.strip())
                
    if main_data.get("brand"): 
        final_tags.append(main_data["brand"].strip())
        
    final_tags.append(main_data["asin"])
    final_tags = list(set(final_tags))
    
    return extracted_categories, final_tags