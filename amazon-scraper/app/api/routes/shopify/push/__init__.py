# app/api/routes/shopify/push/__init__.py
from fastapi import APIRouter

# Import routes
from .add_product import router as add_product_router
from .settings import router as settings_router
from .sync import router as sync_router       # ✅ Sync Router Import karein
from .delete import router as delete_router   # ✅ Delete Router Import karein

# Ek main router banayein jo sabko combine kare
router = APIRouter()

# Saare routes ko is main router mein include karein
router.include_router(add_product_router)
router.include_router(settings_router)
router.include_router(sync_router)            # ✅ Sync Router Include karein
router.include_router(delete_router)          # ✅ Delete Router Include karein