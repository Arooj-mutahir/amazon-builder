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
        # 1. Latest products fetch karo
        print("Fetching products...")
        query_products = """
        query {
          products(first: 5, sortKey: CREATED_AT, reverse: true) {
            edges {
              node {
                id
                title
                handle
                metafields(first: 20) {
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
        r = await client.post(url, json={"query": query_products}, headers=headers)
        data = r.json()
        
        if "errors" in data:
            print(f"❌ API errors: {data['errors']}")
            return
        
        products = data.get("data", {}).get("products", {}).get("edges", [])
        
        if not products:
            print("❌ No products found")
            return
        
        print(f"✅ Found {len(products)} products\n")
        
        # 2. Har product ke metafields print karo
        for p in products:
            node = p["node"]
            mfs = node.get("metafields", {}).get("edges", [])
            print(f"Product: {node['title'][:60]}")
            print(f"  ID: {node['id']}")
            print(f"  Metafields: {len(mfs)}")
            
            if mfs:
                for mf in mfs:
                    m = mf["node"]
                    print(f"    - {m['namespace']}.{m['key']} = {m['value'][:50]} (type: {m['type']})")
            else:
                print(f"    ⚠️  No metafields found")
            print()

asyncio.run(main())