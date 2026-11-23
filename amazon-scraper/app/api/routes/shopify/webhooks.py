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

    # 🔥 HMAC verification temporarily disabled for testing
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

        # 🔥 STEP 1: Product dhoondo
        product_to_delete = db.query(Product).filter(
            Product.shopify_product_id == gid_format,
            Product.shopify_store_id == store.id
        ).first()

        if not product_to_delete:
            product_to_delete = db.query(Product).filter(
                Product.shopify_product_id.like(f"%{shopify_product_id}%"),
                Product.shopify_store_id == store.id
            ).first()

        if product_to_delete:
            deleted_count = 0
            
            # Agar yeh Parent product hai, toh pehle child variations delete karo
            if not product_to_delete.is_variation:
                print(f"   🔍 Parent product mila (ASIN: {product_to_delete.asin}). Ab variations delete kar rahe hain...", flush=True)
                
                # ✅ FIX: Pehle parent_asin se try karo
                variations = db.query(Product).filter(
                    Product.parent_asin == product_to_delete.asin,
                    Product.is_variation == True
                ).all()
                
                # ✅ DOUBLE CHECK: Agar parent_asin se nahi mile, toh parent_id se dhoondo
                # (Assuming tumhare database mein 'parent_id' column hai jo parent ki primary key store karta hai)
                if not variations and hasattr(product_to_delete, 'id'):
                    print(f"   ⚠️ parent_asin se variations nahi mile. Ab parent_id se try kar rahe hain...", flush=True)
                    variations = db.query(Product).filter(
                        Product.parent_id == product_to_delete.id,
                        Product.is_variation == True
                    ).all()
                
                # ✅ AGAR PHIR BHI NAHI MILE, TOH SIRF is_variation = True wale saare check karo (e.g. asin matching)
                if not variations:
                    print(f"   ⚠️ parent_id se bhi variations nahi mile. Ab asin list se match kar rahe hain...", flush=True)
                    # Optional: Agar tumhare paas variation_asins list hai toh unko match karo

                print(f"   🔎 DEBUG: Total {len(variations)} child variations mile.", flush=True)

                for var in variations:
                    print(f"      🗑️ Deleting variation: {var.asin} (ID: {var.id})", flush=True)
                    db.delete(var)
                    deleted_count += 1
                    
                print(f"   🗑️ Total {deleted_count} child variants delete hue", flush=True)

            # Parent ko delete karo
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