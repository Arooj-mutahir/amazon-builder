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

@router.post("/app/webhooks/products-delete")
async def shopify_product_delete_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    print(f"⚠️ [TESTING] HMAC verification disabled for {x_shopify_shop_domain}", flush=True)

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

        # Product dhoondo (Store ID ka check hata diya)
        product_to_delete = db.query(Product).filter(
            Product.shopify_product_id == gid_format
        ).first()

        if not product_to_delete:
            product_to_delete = db.query(Product).filter(
                Product.shopify_product_id == shopify_product_id
            ).first()

        if not product_to_delete:
            product_to_delete = db.query(Product).filter(
                Product.shopify_product_id.like(f"%{shopify_product_id}%")
            ).first()

        if product_to_delete:
            deleted_count = 0
            
            # ✅ FIX: Chahe product parent ho ya variation, uske child variations check karo
            print(f"   🔍 Product mila (ASIN: {product_to_delete.asin}, is_variation: {product_to_delete.is_variation}). Ab variations delete kar rahe hain...", flush=True)
            
            variations = db.query(Product).filter(
                Product.parent_asin == product_to_delete.asin,
                Product.is_variation == True
            ).all()
            
            print(f"   🔎 DEBUG: Total {len(variations)} child variations mile.", flush=True)

            for var in variations:
                print(f"      🗑️ Deleting variation: {var.asin} (ID: {var.id})", flush=True)
                db.delete(var)
                deleted_count += 1

            # Ab main product ko delete karo
            db.delete(product_to_delete)
            deleted_count += 1
            db.commit()
            
            print(f"✅ Database se total {deleted_count} products delete ho gaye (Parent + Variations): {shopify_product_id}", flush=True)
        else:
            print(f"⚠️ Product DB mein nahi mila: {shopify_product_id}", flush=True)

        return {"status": "success"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting product from DB: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")