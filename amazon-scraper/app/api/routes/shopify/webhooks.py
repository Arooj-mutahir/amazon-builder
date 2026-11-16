# app/api/routes/shopify/webhooks.py
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ShopifyStore
import hmac
import hashlib
import base64
import os
import json

router = APIRouter()

# ✅ Secret .env se load karein
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

@router.post("/app/webhooks/products-delete")
async def shopify_product_delete_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    # 1. Raw Body read karein
    body = await request.body()

    # 2. HMAC Verify karein (Security)
    if x_shopify_hmac_sha256 and SHOPIFY_WEBHOOK_SECRET:
        digest = hmac.new(
            SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        computed_hmac = base64.b64encode(digest).decode('utf-8')
        
        if not hmac.compare_digest(computed_hmac, x_shopify_hmac_sha256):
            print(f"❌ Invalid Webhook HMAC from {x_shopify_shop_domain}", flush=True)
            raise HTTPException(status_code=401, detail="Invalid HMAC")
    else:
        print("⚠️ Missing HMAC or Secret. Skipping verification.", flush=True)

    # 3. Data Parse karein
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
        # 4. Store dhoondein (taaki sirf usi store ka product delete ho)
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == x_shopify_shop_domain).first()

        if not store:
            print(f"⚠️ Store not found in DB: {x_shopify_shop_domain}", flush=True)
            return {"status": "ignored", "message": "Store not found"}

        # 5. Database se product dhoondein
        product_to_delete = db.query(Product).filter(
            Product.shopify_product_id.in_([gid_format, shopify_product_id]),
            Product.shopify_store_id == store.id
        ).first()

        if product_to_delete:
            deleted_count = 0
            
            # ✅ Agar Parent product hai, toh uske saare Child variants delete karein
            if not product_to_delete.is_variation:
                child_deleted = db.query(Product).filter(
                    Product.parent_asin == product_to_delete.asin,
                    Product.shopify_store_id == store.id,
                    Product.is_variation == True
                ).delete(synchronize_session=False)
                deleted_count += child_deleted
                print(f"   🗑️ Deleted {child_deleted} child variants", flush=True)

            # ✅ Parent ko delete karein
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