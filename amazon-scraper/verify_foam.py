import asyncio
import httpx
from app.database import SessionLocal
from app.models import ShopifyStore

async def main():
    db = SessionLocal()
    store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == "amazon-product-manager.myshopify.com").first()
    
    if not store:
        print("❌ Store not found")
        return
    
    url = f"https://{store.shop_domain}/admin/api/2024-04/graphql.json"
    headers = {"X-Shopify-Access-Token": store.access_token, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Product ko SKU/ASIN se dhoondho
        print("Searching for product with ASIN B08HDJC2JF...")
        query = """
        query {
          products(first: 50, query: "sku:B08HDJC2JF") {
            edges {
              node {
                id
                title
                handle
                variants(first: 5) {
                  nodes {
                    sku
                  }
                }
                metafields(first: 50) {
                  edges {
                    node {
                      namespace
                      key
                      value
                      type
                    }
                  }
                }
              }
            }
          }
        }
        """
        r = await client.post(url, json={"query": query}, headers=headers)
        data = r.json()
        
        if "errors" in data:
            print(f"❌ API errors: {data['errors']}")
            return
        
        products = data.get("data", {}).get("products", {}).get("edges", [])
        
        if not products:
            print("❌ Product with ASIN B08HDJC2JF not found in Shopify!")
            print("   Shayad product delete ho gaya ya add nahi hua.")
            return
        
        for p in products:
            node = p["node"]
            mfs = node.get("metafields", {}).get("edges", [])
            variants = node.get("variants", {}).get("nodes", [])
            
            print(f"\n✅ FOUND PRODUCT")
            print(f"  Title: {node['title']}")
            print(f"  ID: {node['id']}")
            print(f"  Variants: {len(variants)}")
            for v in variants[:3]:
                print(f"    - SKU: {v.get('sku')}")
            print(f"  Metafields: {len(mfs)}")
            
            if mfs:
                for mf in mfs:
                    m = mf["node"]
                    print(f"    ✓ {m['namespace']}.{m['key']} = {m['value'][:60]} (type: {m['type']})")
            else:
                print(f"  ⚠️  NO METAFIELDS!")

asyncio.run(main())