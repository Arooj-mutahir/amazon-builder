# app/main.py
import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from sqlalchemy import text

# ✅ Router import
from app.api.routes.shopify import router as shopify_router
from app.database import engine, Base, SessionLocal
from app import models
from app.services.scheduler import start_scheduler, scheduler

# ✅ NAYA: Plan system
from app.plan_config import has_feature
from app.deps import _auto_expire
from app.models.product import ShopifyStore

Base.metadata.create_all(bind=engine)


# ============================================================
# 🛠️ AUTO-MIGRATION — Missing columns add karta hai (safe)
# SQLAlchemy create_all() existing tables ko alter nahi karta,
# isliye naye columns manually add karne padte hain.
# ============================================================
REQUIRED_COLUMNS = [
    # (table, column, sql definition)
    ("shopify_stores", "plan", "VARCHAR NOT NULL DEFAULT 'basic'"),
    ("shopify_stores", "plan_status", "VARCHAR NOT NULL DEFAULT 'active'"),
    ("shopify_stores", "plan_expires_at", "TIMESTAMP NULL"),
    ("shopify_stores", "plan_started_at", "TIMESTAMP NULL DEFAULT NOW()"),
    ("shopify_stores", "auto_sync_enabled", "BOOLEAN DEFAULT FALSE"),
    ("shopify_stores", "default_compare_price_markup", "DOUBLE PRECISION DEFAULT 0.0"),
]


def _auto_add_missing_columns():
    """Startup pe missing columns add karta hai — non-destructive."""
    try:
        with engine.begin() as conn:
            for table, col, definition in REQUIRED_COLUMNS:
                exists = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": col},
                ).first()
                if not exists:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                    )
                    print(f"🛠️  Auto-migrated: {table}.{col}", flush=True)
                else:
                    print(f"✅ Column exists: {table}.{col}", flush=True)
    except Exception as e:
        print(f"⚠️ Auto-migration warning: {e}", flush=True)
        # Server band nahi hoga — sirf warning


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_add_missing_columns()   # ⬅️ NAYA
    start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="Amazon to Shopify Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 🛡️ PLAN GUARD MIDDLEWARE
# ============================================================
FEATURE_ROUTES = {
    "/api/shopify/sync/manual": "manual_sync",
    "/api/shopify/sync/auto": "auto_sync",
    "/api/shopify/size-chart": "size_chart",
}


@app.middleware("http")
async def plan_guard(request: Request, call_next):
    path = request.url.path

    # Whitelist
    if (
        path.startswith("/api/shopify/billing")
        or path.startswith("/api/shopify/webhooks/")
        or path == "/"
        or path.startswith("/static")
        or path.startswith("/api/health")
    ):
        return await call_next(request)

    matched_feature = None
    for prefix, feature in FEATURE_ROUTES.items():
        if feature and path.startswith(prefix):
            matched_feature = feature
            break

    if matched_feature:
        db: Session = SessionLocal()
        try:
            shop = request.headers.get("X-Shop-Domain")
            store = (
                db.query(ShopifyStore).filter(ShopifyStore.shop_domain == shop).first()
                if shop
                else db.query(ShopifyStore).first()
            )
            if store:
                store = _auto_expire(store, db)

            if not store or not has_feature(store, matched_feature):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "plan_upgrade_required",
                        "message": f"'{matched_feature}' feature sirf Advance plan mein hai.",
                        "current_plan": store.plan if store else "none",
                        "upgrade_url": "/api/shopify/billing/upgrade",
                    },
                )
        finally:
            db.close()

    return await call_next(request)


# ✅ Routers
app.include_router(shopify_router, prefix="/api/shopify")

# ✅ Billing router
from app.api.routes.billing import router as billing_router
app.include_router(billing_router, prefix="/api/shopify/billing")


@app.get("/")
def read_root(request: Request):
    if "hmac" in request.query_params or "host" in request.query_params:
        params = {}
        if "shop" in request.query_params:
            params["shop"] = request.query_params["shop"]
        if "host" in request.query_params:
            params["host"] = request.query_params["host"]

        qs = urlencode(params)
        frontend_url = "https://ingenious-caring-production-c9aed584.up.railway.app"
        redirect_target = f"{frontend_url}?{qs}" if qs else frontend_url

        return RedirectResponse(url=redirect_target, status_code=302)

    return {"status": "success", "message": "Scraper & Shopify Server is running!"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)