# app/api/routes/shopify/webhooks.py
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ShopifyStore
import hmac
import hashlib
import os
import json

router = APIRouter()

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

@router.post("/app/webhooks/products-delete")
async def shopify_product_delete_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    # ✅ HMAC Verify (Hex Format)
    if x_shopify_hmac_sha256 and SHOPIFY_WEBHOOK_SECRET:
        digest = hmac.new(
            SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(digest, x_shopify_hmac_sha256):
            print(f"❌ Invalid Webhook HMAC from {x_shopify_shop_domain}", flush=True)
            raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        payload = json.loads(body)
        raw_id = payload.get("id")
        if not raw_id:
            return {"status": "ignored", "message": "No product ID"}
        shopify_product_id = str(raw_id)
        gid_format = f"gid://shopify/Product/{shopify_product_id}"
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}", flush=True)
        return {"status": "ignored"}

    print(f"🗑️ Shopify Webhook: Product Deleted {shopify_product_id} (Shop: {x_shopify_shop_domain})", flush=True)

    try:
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == x_shopify_shop_domain).first()
        if not store:
            return {"status": "ignored", "message": "Store not found"}

        product_to_delete = db.query(Product).filter(
            Product.shopify_product_id.in_([gid_format, shopify_product_id]),
            Product.shopify_store_id == store.id
        ).first()

        if product_to_delete:
            deleted_count = 0
            if not product_to_delete.is_variation:
                child_deleted = db.query(Product).filter(
                    Product.parent_asin == product_to_delete.asin,
                    Product.shopify_store_id == store.id,
                    Product.is_variation == True
                ).delete(synchronize_session=False)
                deleted_count += child_deleted
                print(f"   🗑️ Deleted {child_deleted} child variants", flush=True)

            db.delete(product_to_delete)
            deleted_count += 1
            db.commit()
            print(f"✅ Database se {deleted_count} products delete ho gaye: {shopify_product_id}", flush=True)
        else:
            print(f"⚠️ Product DB mein nahi mila: {shopify_product_id}", flush=True)

        return {"status": "success"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting product from DB: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")