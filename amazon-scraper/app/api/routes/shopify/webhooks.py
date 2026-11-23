# app/api/routes/shopify/webhooks.py
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product, ShopifyStore
import hmac
import hashlib
import os
import json
import base64

router = APIRouter()

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")

# ============================================================
# 🗑️ PRODUCT DELETE WEBHOOK
# ============================================================
@router.post("/app/webhooks/products-delete")
async def shopify_product_delete_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    # 🔥 TEMPORARILY DISABLED HMAC VERIFICATION FOR TESTING
    print(f"⚠️ [TESTING] HMAC verification disabled for {x_shopify_shop_domain}", flush=True)
    
    # Original HMAC code (uncomment for production)
    # if x_shopify_hmac_sha256 and SHOPIFY_WEBHOOK_SECRET:
    #     digest = base64.b64encode(
    #         hmac.new(
    #             SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
    #             body,
    #             hashlib.sha256
    #         ).digest()
    #     ).decode('utf-8')
    #     if not hmac.compare_digest(digest, x_shopify_hmac_sha256):
    #         print(f"❌ Invalid Webhook HMAC from {x_shopify_shop_domain}", flush=True)
    #         raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        payload = json.loads(body)
        raw_id = payload.get("id")
        if not raw_id:
            return {"status": "ignored", "message": "No product ID"}
        shopify_product_id = str(raw_id)
        # gid_format = f"gid://shopify/Product/{shopify_product_id}"  # 🔥 No need to use gid format
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}", flush=True)
        return {"status": "ignored"}

    print(f"🗑️ Shopify Webhook: Product Deleted {shopify_product_id} (Shop: {x_shopify_shop_domain})", flush=True)

    try:
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == x_shopify_shop_domain).first()
        if not store:
            return {"status": "ignored", "message": "Store not found"}

        # 🔥 YAHAN FIX: DB mein shopify_product_id gid://shopify/Product/... format mein hai, isliye LIKE use karo
        product_to_delete = db.query(Product).filter(
            Product.shopify_product_id.like(f"%{shopify_product_id}%"),  # 🔥 LIKE query
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


# ============================================================
# 🛑 APP UNINSTALLED WEBHOOK
# ============================================================
@router.post("/app/webhooks/app-uninstalled")
async def shopify_app_uninstalled_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    # 🔥 TEMPORARILY DISABLED HMAC VERIFICATION FOR TESTING
    print(f"⚠️ [TESTING] HMAC verification disabled for {x_shopify_shop_domain}", flush=True)
    
    # Original HMAC code (uncomment for production)
    # if x_shopify_hmac_sha256 and SHOPIFY_WEBHOOK_SECRET:
    #     digest = base64.b64encode(
    #         hmac.new(
    #             SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
    #             body,
    #             hashlib.sha256
    #         ).digest()
    #     ).decode('utf-8')
    #     if not hmac.compare_digest(digest, x_shopify_hmac_sha256):
    #         print(f"❌ Invalid Uninstall HMAC from {x_shopify_shop_domain}", flush=True)
    #         raise HTTPException(status_code=401, detail="Invalid HMAC")

    try:
        payload = json.loads(body)
        shop_domain = payload.get("domain") or payload.get("myshopify_domain") or x_shopify_shop_domain
    except Exception as e:
        print(f"❌ Error parsing Uninstall JSON: {e}", flush=True)
        return {"status": "ignored"}

    print(f"🛑 Shopify Webhook: App Uninstalled (Shop: {shop_domain})", flush=True)

    try:
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop_domain).first()
        
        if store:
            store.access_token = None
            store.refresh_token = None
            store.expires_at = None
            store.refresh_token_expires_at = None
            
            store.plan = "basic"
            store.plan_status = "active"
            store.plan_expires_at = None
            store.auto_sync_enabled = False
            
            store.default_extra_percent = 0.0
            store.default_tax_rate = 0.0
            store.default_compare_price_markup = 0.0

            db.commit()
            print(f"✅ Store '{shop_domain}' uninstalled. Plan reset to BASIC.", flush=True)
        else:
            print(f"⚠️ Store DB mein nahi mila: {shop_domain}", flush=True)

        return {"status": "success"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error handling app uninstall: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")