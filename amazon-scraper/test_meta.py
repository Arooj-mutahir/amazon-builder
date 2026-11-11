import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

# .env file load karein
load_dotenv()

async def main():
    # Aapka asli product ID
    product_id = "gid://shopify/Product/15474548637732"
    
    # Token aur Shop .env se aayenge
    token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    shop = os.getenv("SHOPIFY_SHOP_DOMAIN")

    if not token or not shop:
        print("❌ Error: .env file mein token ya shop domain missing hai!")
        return

    # Test Metafields (jo hum bhej rahe hain)
    metafields = [
        {
            "ownerId": product_id,
            "namespace": "shipping",
            "key": "weight",
            "type": "weight",
            "value": '{"value": 5.2, "unit": "POUNDS"}'
        },
        {
            "ownerId": product_id,
            "namespace": "shipping",
            "key": "length",
            "type": "number_decimal",
            "value": "10.5"
        },
        {
            "ownerId": product_id,
            "namespace": "shipping",
            "key": "width",
            "type": "number_decimal",
            "value": "5.0"
        },
        {
            "ownerId": product_id,
            "namespace": "shipping",
            "key": "height",
            "type": "number_decimal",
            "value": "8.0"
        },
        {
            "ownerId": product_id,
            "namespace": "shipping",
            "key": "dimension_units",
            "type": "single_line_text_field",
            "value": "INCHES"
        }
    ]

    mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields { key namespace }
        userErrors { field message }
      }
    }
    """
    
    url = f"https://{shop}/admin/api/2024-04/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json={"query": mutation, "variables": {"metafields": metafields}}, headers=headers)
        print("Shopify Response:")
        print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())