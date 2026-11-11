from .client import shopify_graphql

async def fetch_all_collections(shop: str, access_token: str) -> list:
    query = """
    query getCollections($cursor: String) {
      collections(first: 50, after: $cursor) {
        edges { node { id title handle } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    collections, has_next, cursor = [], True, None
    while has_next:
        result = await shopify_graphql(shop, access_token, query, {"cursor": cursor})
        if "errors" in result: break
        data = result.get("data", {}).get("collections", {})
        for edge in data.get("edges", []):
            node = edge.get("node", {})
            collections.append({"id": node.get("id"), "title": node.get("title"), "handle": node.get("handle")})
        page_info = data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")
    return collections

async def add_product_to_collections(shop: str, access_token: str, product_id: str, collection_ids: list) -> dict:
    if not collection_ids: return {"success": True}
    mutation = """
    mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
      collectionAddProducts(id: $id, productIds: $productIds) { userErrors { field message } }
    }
    """
    all_ok = True
    for cid in collection_ids:
        res = await shopify_graphql(shop, access_token, mutation, {"id": cid, "productIds": [product_id]})
        if res.get("errors") or res.get("data", {}).get("collectionAddProducts", {}).get("userErrors"):
            all_ok = False
    return {"success": all_ok}