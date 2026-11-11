from ..client import shopify_graphql

async def _set_inventory_quantities(shop, access_token, quantities: list) -> dict:
    if not quantities:
        return {"updated": 0}

    mutation = """
    mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
      inventorySetQuantities(input: $input) {
        inventoryAdjustmentGroup { createdAt reason }
        userErrors { field message }
      }
    }
    """
    payload = {
        "input": {
            "name": "available",
            "reason": "correction",
            "ignoreCompareQuantity": True,
            "quantities": quantities,
        }
    }
    result = await shopify_graphql(shop, access_token, mutation, payload)
    print(f"📊 Inventory API Response: {result}", flush=True)

    user_errors = (result.get("data", {}).get("inventorySetQuantities", {}) or {}).get("userErrors") or []
    if user_errors:
        print(f"❌ inventorySetQuantities errors: {user_errors}", flush=True)
    return {"updated": len(quantities), "errors": user_errors}