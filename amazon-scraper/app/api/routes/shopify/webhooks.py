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

# ============================================
# 1. PRODUCT DELETE WEBHOOK
# ============================================
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


# ============================================
# 2. PRODUCT UPDATE WEBHOOK (NAYA)
# ============================================
@router.post("/app/webhooks/products-update")
async def shopify_product_update_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(None),
    x_shopify_shop_domain: str = Header(None),
    db: Session = Depends(get_db)
):
    body = await request.body()

    print(f"⚠️ [TESTING] HMAC verification disabled for update webhook (Shop: {x_shopify_shop_domain})", flush=True)

    try:
        payload = json.loads(body)
        raw_id = payload.get("id")
        if not raw_id:
            return {"status": "ignored", "message": "No product ID"}
        
        shopify_product_id = str(raw_id)
        gid_format = f"gid://shopify/Product/{shopify_product_id}"
        
        # Shopify se aane wale variants
        variants = payload.get("variants", [])
        
    except Exception as e:
        print(f"❌ Error parsing JSON: {e}", flush=True)
        return {"status": "ignored"}

    print(f"📝 Shopify Webhook: Product Updated {shopify_product_id} (Shop: {x_shopify_shop_domain})", flush=True)

    try:
        store = db.query(ShopifyStore).filter(ShopifyStore.shop_domain == x_shopify_shop_domain).first()
        if not store:
            return {"status": "ignored", "message": "Store not found"}

        # Parent Product dhoondo
        product = db.query(Product).filter(
            Product.shopify_product_id == gid_format
        ).first()
        
        if not product:
            product = db.query(Product).filter(
                Product.shopify_product_id == shopify_product_id
            ).first()
            
        if not product:
            print(f"⚠️ Product DB mein nahi mila: {shopify_product_id}", flush=True)
            return {"status": "ignored", "message": "Product not found in DB"}

        updated_count = 0

        # Agar product ke andar variants hain, toh unka price update karo
        for var in variants:
            shopify_variant_id = str(var.get("id"))
            new_price = var.get("price")
            sku = var.get("sku") # Fallback ke liye SKU bhi nikal lete hain
            
            if not new_price:
                continue
            
            variant_product = None
            
            # 1. Pehle Shopify Variant ID se dhoondo (agar column exist karta hai)
            if hasattr(Product, 'shopify_variant_id'):
                variant_product = db.query(Product).filter(
                    Product.shopify_variant_id == shopify_variant_id
                ).first()
            
            # 2. Agar Variant ID se nahi mila, toh SKU (ASIN) se dhoondo
            if not variant_product and sku:
                variant_product = db.query(Product).filter(
                    Product.asin == sku
                ).first()
            
            if variant_product:
                variant_product.price = float(new_price)
                updated_count += 1
                print(f"   ✅ Updated Variant {shopify_variant_id} (SKU: {sku}) price to {new_price}", flush=True)
            else:
                print(f"   ⚠️ Variant not found in DB: {shopify_variant_id} (SKU: {sku})", flush=True)
        
        # Agar koi variant match nahi hua, toh shayad single product hai
        if updated_count == 0 and variants:
            # Fallback: Parent product ka price update karo pehle variant se
            product.price = float(variants[0].get("price", product.price))
            updated_count += 1
            print(f"   ✅ Fallback: Updated Parent Product price to {product.price}", flush=True)

        db.commit()
        print(f"✅ Total {updated_count} prices updated in DB for product {shopify_product_id}", flush=True)
        
        return {"status": "success"}

    except Exception as e:
        db.rollback()
        print(f"❌ Error updating product price: {e}", flush=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")