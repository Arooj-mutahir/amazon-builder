from .client import shopify_graphql

async def get_primary_location(shop: str, access_token: str) -> str:
    query = """
    query getLocations {
      locations(first: 1, includeInactive: false) {
        nodes { id name isActive }
      }
    }
    """
    result = await shopify_graphql(shop, access_token, query, {})
    try:
        locations = (result.get("data") or {}).get("locations", {}).get("nodes") or []
        if locations:
            loc = locations[0]
            print(f"📍 Using first location: {loc['name']} ({loc['id']})", flush=True)
            return loc["id"]
    except Exception as e:
        print(f"⚠️ Location fetch failed: {e}", flush=True)
    return None


async def get_shopify_category_id(shop: str, access_token: str, amazon_categories: list) -> str:
    if not amazon_categories:
        # Agar categories khali hain toh default "Toys" (ya general) set kar do
        return "gid://shopify/TaxonomyCategory/hg-3-2" 
        
    search_terms = []
    
    # 1. Amazon categories array ko reverse karo (sabse specific pehle check karo)
    reversed_cats = list(reversed(amazon_categories))
    
    for cat in reversed_cats:
        if ">" in cat:
            parts = [p.strip() for p in cat.split(">")]
            for p in reversed(parts):
                if p and p not in search_terms:
                    search_terms.append(p)
        else:
            clean_cat = cat.strip()
            if clean_cat and clean_cat not in search_terms:
                search_terms.append(clean_cat)

    # 2. Fallback Terms (Agar direct match na mile)
    fallback_terms = ["Toys & Games", "Toys", "Vehicles", "Trucks", "Cars", "Hobbies", "Home & Kitchen"]
    for f_term in fallback_terms:
        if f_term not in search_terms:
            search_terms.append(f_term)

    # Sirf top 8 unique terms check karo
    search_terms = list(dict.fromkeys(search_terms))[:8]
    
    query = """
    query getCategory($search: String!) {
      taxonomy {
        categories(first: 1, search: $search) {
          edges { node { id name } }
        }
      }
    }
    """
    
    for term in search_terms:
        if not term or len(term) < 3: continue
        
        # Kuch words ko clean karo (jaise "&" aur "'" hata do)
        clean_term = term.replace("&", "").replace("'", "").strip()
        if not clean_term: continue

        print(f"🔍 Searching Shopify Category for: '{clean_term}'", flush=True)
        
        result = await shopify_graphql(shop, access_token, query, {"search": clean_term})
        
        try:
            edges = result.get('data', {}).get('taxonomy', {}).get('categories', {}).get('edges', [])
            if edges:
                matched_id = edges[0]['node']['id']
                matched_name = edges[0]['node']['name']
                print(f"✅ Matched Category: {matched_name} ({matched_id})", flush=True)
                return matched_id
        except Exception as e:
            print(f"⚠️ Category search error: {e}", flush=True)

    print("⚠️ No matching Shopify category found. Using default.", flush=True)
    return "gid://shopify/TaxonomyCategory/hg-3-2" # Default Toys Category ID agar sab fail ho jaye


async def publish_product(shop: str, access_token: str, product_id: str) -> dict:
    print(f"📢 Publishing product {product_id}...", flush=True)
    query_pub = "query getPublications { publications(first: 10) { edges { node { id name } } } }"
    pub_res = await shopify_graphql(shop, access_token, query_pub)
    
    if "errors" in pub_res: 
        print(f"❌ Error fetching publications: {pub_res['errors']}", flush=True)
        return pub_res

    publications = pub_res.get("data", {}).get("publications", {}).get("edges", [])
    if not publications:
        print("❌ No publications found in this store!", flush=True)
        return {"success": False, "message": "No publications found"}

    # ✅ Pehla publication utha lein (chahe uska naam kuch bhi ho)
    online_store_id = publications[0]["node"]["id"]
    pub_name = publications[0]["node"]["name"]
    print(f"✅ Using Publication: {pub_name} ({online_store_id})", flush=True)

    mutation = """
    mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) { userErrors { field message } }
    }
    """
    result = await shopify_graphql(shop, access_token, mutation, {"id": product_id, "input": [{"publicationId": online_store_id}]})
    
    # ✅ Error check aur print karein
    if "errors" in result:
        print(f"❌ Publish GraphQL Error: {result['errors']}", flush=True)
    else:
        user_errors = result.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
        if user_errors:
            print(f"❌ Publish User Errors: {user_errors}", flush=True)
        else:
            print(f"✅ Product {product_id} published successfully to {pub_name}!", flush=True)
            
    return result


async def get_shopify_category_id(shop: str, access_token: str, amazon_categories: list) -> str:
    if not amazon_categories:
        # Agar categories khali hain toh default "Toys" (ya general) set kar do
        return "gid://shopify/TaxonomyCategory/hg-3-2" 
        
    search_terms = []
    
    # 1. Amazon categories array ko reverse karo (sabse specific pehle check karo)
    reversed_cats = list(reversed(amazon_categories))
    
    for cat in reversed_cats:
        if ">" in cat:
            parts = [p.strip() for p in cat.split(">")]
            for p in reversed(parts):
                if p and p not in search_terms:
                    search_terms.append(p)
        else:
            clean_cat = cat.strip()
            if clean_cat and clean_cat not in search_terms:
                search_terms.append(clean_cat)

    # 2. Fallback Terms (Agar direct match na mile)
    fallback_terms = ["Toys & Games", "Toys", "Vehicles", "Trucks", "Cars", "Hobbies", "Home & Kitchen"]
    for f_term in fallback_terms:
        if f_term not in search_terms:
            search_terms.append(f_term)

    # Sirf top 8 unique terms check karo
    search_terms = list(dict.fromkeys(search_terms))[:8]
    
    query = """
    query getCategory($search: String!) {
      taxonomy {
        categories(first: 1, search: $search) {
          edges { node { id name } }
        }
      }
    }
    """
    
    for term in search_terms:
        if not term or len(term) < 3: continue
        
        # Kuch words ko clean karo (jaise "&" aur "'" hata do)
        clean_term = term.replace("&", "").replace("'", "").strip()
        if not clean_term: continue

        print(f"🔍 Searching Shopify Category for: '{clean_term}'", flush=True)
        
        result = await shopify_graphql(shop, access_token, query, {"search": clean_term})
        
        try:
            edges = result.get('data', {}).get('taxonomy', {}).get('categories', {}).get('edges', [])
            if edges:
                matched_id = edges[0]['node']['id']
                matched_name = edges[0]['node']['name']
                print(f"✅ Matched Category: {matched_name} ({matched_id})", flush=True)
                return matched_id
        except Exception as e:
            print(f"⚠️ Category search error: {e}", flush=True)

    print("⚠️ No matching Shopify category found. Using default.", flush=True)
    return "gid://shopify/TaxonomyCategory/hg-3-2" # Default Toys Category ID agar sab fail ho jaye


async def publish_product(shop: str, access_token: str, product_id: str) -> dict:
    print(f"📢 Publishing product {product_id}...", flush=True)
    query_pub = "query getPublications { publications(first: 10) { edges { node { id name } } } }"
    pub_res = await shopify_graphql(shop, access_token, query_pub)
    
    if "errors" in pub_res: 
        print(f"❌ Error fetching publications: {pub_res['errors']}", flush=True)
        return pub_res

    publications = pub_res.get("data", {}).get("publications", {}).get("edges", [])
    if not publications:
        print("❌ No publications found in this store!", flush=True)
        return {"success": False, "message": "No publications found"}

    # ✅ Pehla publication utha lein (chahe uska naam kuch bhi ho)
    online_store_id = publications[0]["node"]["id"]
    pub_name = publications[0]["node"]["name"]
    print(f"✅ Using Publication: {pub_name} ({online_store_id})", flush=True)

    mutation = """
    mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
      publishablePublish(id: $id, input: $input) { userErrors { field message } }
    }
    """
    result = await shopify_graphql(shop, access_token, mutation, {"id": product_id, "input": [{"publicationId": online_store_id}]})
    
    # ✅ Error check aur print karein
    if "errors" in result:
        print(f"❌ Publish GraphQL Error: {result['errors']}", flush=True)
    else:
        user_errors = result.get("data", {}).get("publishablePublish", {}).get("userErrors", [])
        if user_errors:
            print(f"❌ Publish User Errors: {user_errors}", flush=True)
        else:
            print(f"✅ Product {product_id} published successfully to {pub_name}!", flush=True)
            
    return result