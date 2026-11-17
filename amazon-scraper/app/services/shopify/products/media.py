from ..client import shopify_graphql

async def _upload_media_and_get_id(shop: str, access_token: str, product_id: str, image_url: str):
    mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
      productCreateMedia(productId: $productId, media: $media) {
        media {
          ... on MediaImage {
            id
            image { url }
          }
        }
        mediaUserErrors { field message code }
      }
    }
    """
    if not image_url.startswith("http"):
        image_url = "https://" + image_url

    resp = await shopify_graphql(shop, access_token, mutation, {
        "productId": product_id,
        "media": [{"originalSource": image_url, "mediaContentType": "IMAGE"}],
    })
    errs = (resp.get("data", {}).get("productCreateMedia") or {}).get("mediaUserErrors") or []
    if errs:
        print(f"⚠️  productCreateMedia error for {image_url[-60:]}: {errs}", flush=True)
        return None
    nodes = (resp.get("data", {}).get("productCreateMedia") or {}).get("media") or []
    if nodes and nodes[0].get("id"):
        media_id = nodes[0]["id"]
        print(f"✅ Uploaded media: {media_id} ← {image_url[-60:]}", flush=True)
        return media_id
    return None

async def _attach_variant_images(shop, access_token, product_id, product_media, product_variants, per_variant_options, gallery_urls=None):
    print(f"🖼️  Attaching per-variant images to {len(product_variants)} variants...", flush=True)
    if not product_variants:
        return

    url_to_media_id = {}
    for m in product_media or []:
        if m.get("image") and m["image"].get("url") and m.get("id"):
            clean_url = m["image"]["url"].split("?")[0].rstrip("/")
            url_to_media_id[clean_url] = m["id"]

    sku_to_variant_id = {
        str(v.get("sku", "")).strip().lower(): v["id"]
        for v in product_variants if v.get("sku") and v.get("id")
    }

    updates = []
    for entry in per_variant_options or []:
        asin = str(entry.get("asin", "")).strip().lower()
        variant_id = sku_to_variant_id.get(asin)
        v_images = entry.get("images") or []

        if not variant_id or not v_images:
            continue

        target_url = v_images[0].split("?")[0].rstrip("/")
        media_id = url_to_media_id.get(target_url)

        if not media_id:
            target_fname = target_url.split("/")[-1]
            for s_url, m_id in url_to_media_id.items():
                if s_url.endswith(target_fname):
                    media_id = m_id
                    break

        if not media_id:
            media_id = await _upload_media_and_get_id(shop, access_token, product_id, v_images[0])

        if media_id:
            updates.append({"id": variant_id, "mediaId": media_id})
            print(f"✅ Matched image for ASIN {asin} → mediaId {media_id[-8:]}", flush=True)

    if not updates:
        return

    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants { id }
        userErrors { field message }
      }
    }
    """
    resp = await shopify_graphql(shop, access_token, mutation, {"productId": product_id, "variants": updates})
    errs = (resp.get("data", {}).get("productVariantsBulkUpdate") or {}).get("userErrors") or []
    if not errs:
        print(f"✅ Attached correct images to {len(updates)} variants successfully", flush=True)