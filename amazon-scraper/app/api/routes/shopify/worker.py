# app/api/routes/shopify/worker.py
import traceback
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ShopifyStore, Product
from app.services.amazon_bridge import get_shopify_product_data

from app.worker.single_product import process_single_variant
from app.worker.variants_product import process_multi_variant
from app.worker.sync_job import sync_prices_job

from .helpers import (
    extract_asin_from_url, _resolve_markup, calculate_final_price, _build_clean_variants, _get_valid_access_token
)
from app.worker.stock_utils import _get_availability, _resolve_stock

router = APIRouter()

async def _background_fetch_and_push(
    amazon_url: str, shop_domain: str, store_id: int, 
    markup, markup_type, extra_percent, tax_rate, 
    compare_price_markup: float = 0.0,
    collection_ids: list = None
):
    print(f"\n🔥🔥🔥 BACKGROUND JOB STARTED for {amazon_url} 🔥🔥🔥", flush=True)

    # PHASE 1: Store fetch & TRIAL/LIMIT CHECK
    db = SessionLocal()
    try:
        store = db.query(ShopifyStore).filter(ShopifyStore.id == store_id).first()
        if not store:
            print("❌ Store not found", flush=True)
            return

        if store.trial_ends_at and store.trial_ends_at < datetime.utcnow():
            if store.plan_status == "active" and not store.plan_expires_at:
                print(f"⏰ TRIAL EXPIRED: Store {store.shop_domain}. Import blocked.", flush=True)
                return

        if (store.plan or "").lower() == "basic":
            limit = 1000
        else:
            limit = 10000

        current_count = store.product_count or 0
        if current_count >= limit:
            print(f"🚫 LIMIT REACHED: Store {store.shop_domain} has {current_count}/{limit} products. Import blocked.", flush=True)
            return

        asin_quick = extract_asin_from_url(amazon_url)
        if not asin_quick:
            print(f"❌ Could not extract ASIN from {amazon_url}", flush=True)
            return

        user_markup, user_markup_type, user_extra, user_tax = _resolve_markup(
            store, markup, markup_type, extra_percent, tax_rate
        )

        print(f"⚙️ [UI FETCH] Markup={user_markup}, Type={user_markup_type}, Extra={user_extra}%, Tax={user_tax}%, Compare={compare_price_markup}%", flush=True)
        default_stock_qty = getattr(store, "default_stock_qty", 0) or 0

        store_id_local = store.id
        store_domain_local = store.shop_domain
        store_plan = store.plan

    finally:
        try:
            db.close()
        except:
            pass

    # PHASE 2: Scraping
    try:
        main_data = await get_shopify_product_data(asin_quick, default_stock_qty=default_stock_qty)
        print(f"✅ Bridge Data Fetched: {str(main_data.get('title'))[:60]}...", flush=True)
        print(f"📏 Size Chart Length: {len(main_data.get('size_chart') or '')}", flush=True)
    except Exception as e:
        print(f"❌ Bridge Fetch fail: {e}", flush=True)
        traceback.print_exc()
        return

    # PHASE 3: Data process
    final_price = calculate_final_price(
        main_data.get("price", 0.0), user_markup, user_markup_type, user_extra, user_tax
    )

    extracted_categories = main_data.get("tags") or []
    final_tags = []
    for cat in extracted_categories:
        if ">" in cat:
            parts = [p.strip() for p in cat.split(">")]
            final_tags.extend(parts)
        else:
            if cat.strip():
                final_tags.append(cat.strip())
    if main_data.get("brand"):
        final_tags.append(main_data["brand"].strip())
    final_tags.append(main_data["asin"])
    final_tags = list(set(final_tags))

    # 🔥 FIX: Seedha main_data se is_add_to_cart_visible uthao
    parent_in_stock = main_data.get("is_add_to_cart_visible", False)
    parent_stock = 100 if parent_in_stock else 0
    
    print(f"📦 [WORKER] Parent Stock: {parent_stock} | In Stock: {parent_in_stock}", flush=True)

    shopify_payload = {
        "title":        main_data.get("title"),
        "description":  main_data.get("description", ""),
        "bullets":      main_data.get("bullets") or [],
        "size_chart":   main_data.get("size_chart") or "",
        "reviews":      main_data.get("reviews") or [],
        "brand":        main_data.get("brand"),
        "images":       main_data.get("images") or [],
        "price":        final_price,
        "tags":         final_tags,
        "categories":   extracted_categories,
        "product_type": extracted_categories[-1] if extracted_categories else "General",
        "asin":         main_data.get("asin"),
        "details":      main_data.get("details") or {},
        "is_available": parent_in_stock,
        "in_stock":     parent_in_stock,
        "stock_quantity": parent_stock,
    }
    
    clean_variants = _build_clean_variants(main_data, [])
    variants_by_asin = {v["asin"]: v for v in (main_data.get("variant_products") or []) if v.get("asin")}
    
    for v in clean_variants:
        v_asin = v.get("asin")
        bridge_v = variants_by_asin.get(v_asin)
        if bridge_v:
            if bridge_v.get("price") and bridge_v["price"] > 0:
                v["price"] = bridge_v["price"]
            # 🔥 FIX: Har variation ko bhi parent ka stock do
            v["in_stock"] = parent_in_stock
            v["stock_qty"] = parent_stock

    # PHASE 4: DB Save
    db2 = SessionLocal()
    try:
        store_fresh = db2.query(ShopifyStore).filter(ShopifyStore.id == store_id_local).first()
        if not store_fresh:
            print("❌ Store disappeared during scraping", flush=True)
            return

        if store_fresh.trial_ends_at and store_fresh.trial_ends_at < datetime.utcnow():
            if store_fresh.plan_status == "active" and not store_fresh.plan_expires_at:
                print(f"⏰ TRIAL EXPIRED DURING SCRAPE: {store_fresh.shop_domain}. Import blocked.", flush=True)
                return

        if (store_fresh.plan or "").lower() == "basic":
            limit = 1000
        else:
            limit = 10000

        current_count = store_fresh.product_count or 0
        if current_count >= limit:
            print(f"🚫 LIMIT REACHED DURING SCRAPE: {current_count}/{limit}. Import blocked.", flush=True)
            return

        if clean_variants and len(clean_variants) > 0:
            print(f"🆕 Creating MULTI-VARIANT product with {len(clean_variants)} variants...", flush=True)
            await process_multi_variant(
                store=store_fresh, main_data=main_data, clean_variants=clean_variants,
                user_markup=user_markup, user_markup_type=user_markup_type, user_extra=user_extra, user_tax=user_tax,
                final_tags=final_tags, extracted_categories=extracted_categories, 
                shopify_payload=shopify_payload, shop_domain=shop_domain, collection_ids=collection_ids, 
                db=db2, default_stock_qty=default_stock_qty,
                compare_price_markup=compare_price_markup
            )
        else:
            print(f"🆕 Creating SINGLE-VARIANT product...", flush=True)
            await process_single_variant(
                store=store_fresh, main_data=main_data, 
                user_markup=user_markup, user_markup_type=user_markup_type, user_extra=user_extra, user_tax=user_tax,
                final_tags=final_tags, extracted_categories=extracted_categories, 
                shopify_payload=shopify_payload, shop_domain=shop_domain, db=db2, default_stock_qty=default_stock_qty,
                compare_price_markup=compare_price_markup,
                collection_ids=collection_ids
            )

    except Exception as e:
        print(f"\n❌ SAVE CRASHED: {e}", flush=True)
        traceback.print_exc()
        try:
            db2.rollback()
        except:
            pass
    finally:
        try:
            if db2.is_active:
                db2.close()
        except:
            pass


# ============================================================
# 🚀 MANUAL SYNC ENDPOINT
# ============================================================
@router.post("/manual-sync")
async def trigger_manual_sync(
    store_id: int = Query(..., description="Store ID to sync"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    store = db.query(ShopifyStore).filter(ShopifyStore.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    if (store.plan or "").lower() != "advance":
        raise HTTPException(status_code=403, detail="Manual sync is only available for Advance plan.")

    print(f"🔄 [MANUAL SYNC] Triggered for store {store.shop_domain} (ID: {store.id})", flush=True)
    
    background_tasks.add_task(sync_prices_job, store_id=store.id)

    return {
        "status": "success",
        "message": f"Manual sync started for {store.shop_domain}. Check logs for progress.",
        "store_id": store.id
    }