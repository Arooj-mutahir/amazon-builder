import asyncio
from dotenv import load_dotenv
load_dotenv()
from app.database import SessionLocal
from app.models import Product, ShopifyStore
from app.services.shopify.client import shopify_graphql
from app.services.shopify.metafields import _build_description_with_metafields

async def main():
    db = SessionLocal()
    p = db.query(Product).order_by(Product.id.desc()).first()
    s = db.query(ShopifyStore).filter(ShopifyStore.id == p.shopify_store_id).first()
    
    # First get the current description and size chart from Shopify
    query = """
    query getProd($id: ID!) {
      product(id: $id) {
        id
        title
        descriptionHtml
      }
    }
    """
    res = await shopify_graphql(s.shop_domain, s.access_token, query, {"id": p.shopify_product_id})
    desc = res.get("data", {}).get("product", {}).get("descriptionHtml", "")
    
    # Check if size-chart-wrapper exists in the desc
    idx_sc = desc.find("<div class='size-chart-wrapper'")
    if idx_sc != -1:
        # Find closing of size-chart-wrapper
        closing = "</details>\n</div>"
        idx_close = desc.find(closing, idx_sc)
        if idx_close != -1:
            sc_block = desc[idx_sc : idx_close + len(closing)]
            # Remove from old position
            rest = desc[:idx_sc] + desc[idx_close + len(closing):]
            # Put sc_block right at the very beginning!
            new_desc = sc_block + "\n\n" + rest.strip()
            
            # Now update Shopify product description
            mutation = """
            mutation updateProduct($input: ProductInput!) {
              productUpdate(input: $input) {
                product {
                  id
                  title
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            update_res = await shopify_graphql(s.shop_domain, s.access_token, mutation, {
                "input": {
                    "id": p.shopify_product_id,
                    "descriptionHtml": new_desc
                }
            })
            print("Shopify Update Result:", update_res)
            print("✅ Successfully updated live product on Shopify! Size Chart is now at the VERY TOP!")
    else:
        print("Could not find size-chart-wrapper in description")
    db.close()

if __name__ == "__main__":
    asyncio.run(main())

