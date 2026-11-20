# app/api/routes/shopify/__init__.py
from fastapi import APIRouter
from . import install, collections, push, stores, webhooks, token_exchange  
router = APIRouter()

router.include_router(install.router)
router.include_router(collections.router)
router.include_router(push.router)
router.include_router(stores.router)
router.include_router(webhooks.router)
router.include_router(token_exchange.router)  