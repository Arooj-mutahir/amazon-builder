from fastapi import APIRouter
from . import install, collections, push

# ✅ Yahan koi prefix nahi hoga
router = APIRouter()

router.include_router(install.router)
router.include_router(collections.router)
router.include_router(push.router)