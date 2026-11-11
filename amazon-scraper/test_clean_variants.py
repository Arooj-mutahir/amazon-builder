import asyncio
from app.services.amazon_bridge import get_shopify_product_data
from app.api.routes.shopify_routes import _build_clean_variants

async def main():
    # 1. Main product fetch
    main_data = await get_shopify_product_data("B08HDJC2JF")
    
    # 2. Child variants fetch
    variant_asins = [
        vp["asin"] for vp in main_data.get("variant_products", []) or []
        if vp.get("asin") and vp["asin"] != "B08HDJC2JF"
    ]
    
    fetched_variants = []
    for v_asin in variant_asins:
        try:
            v_data = await get_shopify_product_data(v_asin)
            fetched_variants.append(v_data)
        except Exception as e:
            print(f"Failed {v_asin}: {e}")
    
    # 3. Build clean variants
    clean_variants = _build_clean_variants(main_data, fetched_variants)
    
    print("\n=== CLEAN VARIANTS (from _build_clean_variants) ===")
    for cv in clean_variants:
        img = str(cv.get('image'))[:90]
        print(f"  ASIN={cv.get('asin'):15} img={img}")
    print()

asyncio.run(main())