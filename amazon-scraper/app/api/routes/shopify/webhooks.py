# app/api/routes/shopify/webhooks.py
from fastapi import APIRouter, Request, Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product
import hmac
import hashlib
import base64

router = APIRouter()

@router.post("/app/webhooks/products-delete")
async def shopify_product_delete_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    # 1. Security Check (Verify request is actually from Shopify)
    body = await request.body()
    # Yahan aapko apna SHOPIFY_API_SECRET use karna hoga
    # (Note: Abhi ke liye hum isko skip kar rahe hain, lekin production ke liye zaroori hai)
    
    # 2. Data Parse karein
    import json
    try:
        payload = json.loads(body)
        shopify_product_id = str(payload.get("id"))
        asin = payload.get("handle") # Shopify handle aam tor par ASIN hota hai
    except Exception:
        return {"status": "ignored"}

    print(f"🗑️ Shopify Webhook: Product Deleted {shopify_product_id} (Shop: {x_shopify_shop_domain})", flush=True)

    if shopify_product_id:
        # 3. Database se delete karein
        # Hum ID ya Handle (ASIN) dono se dhoond sakte hain
        product_to_delete = db.query(Product).filter(
            (Product.shopify_product_id == shopify_product_id) | 
            (Product.shopify_product_id == f"gid://shopify/Product/{shopify_product_id}")
        ).first()

        if product_to_delete:
            db.delete(product_to_delete)
            db.commit()
            print(f"✅ Database se product delete ho gaya: {shopify_product_id}", flush=True)
        else:
            print(f"⚠️ Product DB mein nahi mila: {shopify_product_id}", flush=True)

    return {"status": "success"}