# app/api/routes/shopify/worker.py
import traceback
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.models import ShopifyStore
from app.services.amazon_bridge import get_shopify_product_data
from app.worker.sync_job import sync_prices_job
from app.worker.single_product import process_single_variant
from app.worker.variants_product import process_multi_variant

from .helpers import (
    extract_asin_from_url, _resolve_markup, calculate_final_price, _build_clean_variants, _get_valid_access_token
)
from app.worker.stock_utils import _get_availability, _resolve_stock

async def _background_fetch_and_push(
    amazon_url: str, shop_domain: str, store_id: int, 
    markup, markup_type, extra_percent, tax_rate, collection_ids: list
):
    db = SessionLocal()
    try:
        print(f"\n🔥🔥🔥 BACKGROUND JOB STARTED for {amazon_url} 🔥🔥🔥", flush=True)
        store = db.query(ShopifyStore).filter(ShopifyStore.id == store_id).first()
        if not store:
            print("❌ Store not found", flush=True); return

        asin_quick = extract_asin_from_url(amazon_url)
        if not asin_quick:
            print(f"❌ Could not extract ASIN from {amazon_url}", flush=True); return

        user_markup, user_markup_type, user_extra, user_tax = _resolve_markup(
            store, markup, markup_type, extra_percent, tax_rate
        )

        print(f"⚙️ [UI FETCH] Markup={user_markup}, Type={user_markup_type}, Extra={user_extra}%, Tax={user_tax}%", flush=True)
        default_stock_qty = getattr(store, "default_stock_qty", 0) or 0

        try:
            main_data = await get_shopify_product_data(asin_quick, default_stock_qty=default_stock_qty)
            print(f"✅ Bridge Data Fetched: {str(main_data.get('title'))[:60]}...", flush=True)
        except Exception as e:
            print(f"❌ Bridge Fetch fail: {e}", flush=True); traceback.print_exc(); return

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
                if cat.strip(): final_tags.append(cat.strip())
        if main_data.get("brand"): final_tags.append(main_data["brand"].strip())
        final_tags.append(main_data["asin"])
        final_tags = list(set(final_tags))

        parent_available = _get_availability(main_data)
        parent_stock_qty = _resolve_stock(parent_available, main_data.get("stock_qty"), default_stock_qty)
        parent_in_stock = bool(parent_available) if parent_stock_qty is not None else False
        parent_stock = parent_stock_qty or 0

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
            "stock_qty":    parent_stock,
        }
        
        clean_variants = _build_clean_variants(main_data, [])
        variants_by_asin = {v["asin"]: v for v in (main_data.get("variant_products") or []) if v.get("asin")}
        
        for v in clean_variants:
            v_asin = v.get("asin")
            bridge_v = variants_by_asin.get(v_asin)
            if bridge_v:
                if bridge_v.get("price") and bridge_v["price"] > 0:
                    v["price"] = bridge_v["price"]
                v["in_stock"] = _get_availability(bridge_v)
                v["stock_qty"] = bridge_v.get("stock_qty")

        if clean_variants and len(clean_variants) > 0:
            print(f"🆕 Creating MULTI-VARIANT product with {len(clean_variants)} variants...", flush=True)
            await process_multi_variant(
                store=store, main_data=main_data, clean_variants=clean_variants,
                user_markup=user_markup, user_markup_type=user_markup_type, user_extra=user_extra, user_tax=user_tax,
                final_tags=final_tags, extracted_categories=extracted_categories, 
                shopify_payload=shopify_payload, shop_domain=shop_domain, collection_ids=collection_ids, 
                db=db, default_stock_qty=default_stock_qty
            )
        else:
            print(f"🆕 Creating SINGLE-VARIANT product...", flush=True)
            await process_single_variant(
                store=store, main_data=main_data, 
                user_markup=user_markup, user_markup_type=user_markup_type, user_extra=user_extra, user_tax=user_tax,
                final_tags=final_tags, extracted_categories=extracted_categories, 
                shopify_payload=shopify_payload, shop_domain=shop_domain, db=db, default_stock_qty=default_stock_qty
            )
            
    except Exception as e:
        print(f"\n❌ CRASHED: {e}", flush=True); traceback.print_exc()
    finally: 
        db.close()

# Scheduler Setup
scheduler = AsyncIOScheduler()

async def run_price_update_now():
    print("⚡ [MANUAL TRIGGER] Price + Stock Sync Started...", flush=True)
    await sync_prices_job()

def start_scheduler():
    scheduler.add_job(
        sync_prices_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="price_sync_job",
        name="Sync Amazon Prices & Stock to Shopify",
        replace_existing=True,
    )
    scheduler.start()
    print("🚀 CRON JOB SCHEDULED: Har raat 2 baje price + stock check hoga.")