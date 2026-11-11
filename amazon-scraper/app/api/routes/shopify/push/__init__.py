from fastapi import APIRouter

# Import routes
from .add_product import router as add_product_router
from .settings import router as settings_router

# Ek main router banayein jo sabko combine kare
router = APIRouter()

# Saare routes ko is main router mein include karein
router.include_router(add_product_router)
router.include_router(settings_router)