from fastapi import APIRouter
from . import install, collections, push, stores

router = APIRouter()

router.include_router(install.router)
router.include_router(collections.router)
router.include_router(push.router)
router.include_router(stores.router) # <-- Yeh line add karein