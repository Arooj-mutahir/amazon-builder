# app/services/shopify.py
# v9 — Fixed pricing, dynamic stock, no hardcoded 100/location
import logging
from app.services.shopify_auth import (
    build_auth_url, verify_hmac, verify_id_token,
    exchange_code_for_token, exchange_id_token_for_offline_token,
    refresh_shopify_token
)
from .client import shopify_graphql
from .locations import get_primary_location, get_shopify_category_id, publish_product
from .collections import fetch_all_collections, add_product_to_collections
from .metafields import set_product_metafields_smart, _build_description_with_metafields
from .products import (
    create_shopify_product,
    create_shopify_product_with_variants,
    _attach_variant_images,
    _set_inventory_quantities,   
)


# Stubs jo abhi use nahi ho rahe par import error na aaye
async def add_variant_to_existing_product(*args, **kwargs): return {'errors': [{'message': 'Not implemented'}]}
async def get_shopify_product_by_sku(*args, **kwargs): return None
async def update_shopify_product_status(*args, **kwargs): return True
async def set_inventory_quantity(*args, **kwargs): return True
async def sync_update_shopify_price(*args, **kwargs): return True
async def set_product_metafields(*args, **kwargs): return True