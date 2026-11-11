import httpx
from app.config import settings

def _api_version() -> str:
    return getattr(settings, "SHOPIFY_API_VERSION", "2024-04")

async def shopify_graphql(shop: str, token: str, query: str, variables: dict = None) -> dict:
    url = f"https://{shop}/admin/api/{_api_version()}/graphql.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
        
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            # ✅ Agar API fail hoti hai, toh seedha error return karo
            if response.status_code != 200:
                print(f"❌ Shopify API Error {response.status_code}: {response.text[:200]}", flush=True)
                return {"errors": [{"message": f"HTTP {response.status_code}: {response.text[:200]}"}]}
                
            return response.json()
    except Exception as e:
        print(f"❌ Shopify GraphQL Exception: {e}", flush=True)
        return {"errors": [{"message": str(e)}]}