# app/models/product.py (ya app/models.py)
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class ShopifyStore(Base):
    __tablename__ = "shopify_stores"
    id = Column(Integer, primary_key=True, index=True)
    shop_domain = Column(String, unique=True, index=True)
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    refresh_token_expires_at = Column(DateTime, nullable=True)
    scopes = Column(String, nullable=True)
    installed_at = Column(DateTime, default=datetime.utcnow)
    
    # Settings
    default_markup = Column(Float, default=0.0)             
    default_markup_type = Column(String, default="fixed")    # ✅ Default fallback
    default_extra_percent = Column(Float, default=0.0)       
    default_tax_rate = Column(Float, default=0.0)            
    default_stock_qty = Column(Integer, default=0)   
    
    # ✅ NEW: Stock settings (optional lekin recommended)
    default_stock_qty = Column(Integer, default=100)          # ✅
    shopify_location_id = Column(String, nullable=True)       # ✅ cache


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String, unique=True, index=True)
    parent_asin = Column(String, nullable=True)
    is_variation = Column(Boolean, default=False)
    title = Column(String)
    brand = Column(String, nullable=True)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    images = Column(JSON, default=list)
    
    # Pricing
    price = Column(Float)
    amazon_price = Column(Float)
    list_price = Column(Float, nullable=True)
    markup = Column(Float, default=0.0)
    markup_type = Column(String, default="percent")
    extra_percent = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    
    # Inventory & Availability
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    availability = Column(String, default="In Stock")
    
    # Variations & Attributes
    variant_attributes = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    specifications = Column(JSON, default=dict)
    
    # Amazon Details
    rating = Column(Float, nullable=True)
    reviews_count = Column(Integer, nullable=True)
    item_weight = Column(String, nullable=True)
    item_dimensions = Column(String, nullable=True)
    
    # Shopify Integration
    shopify_product_id = Column(String, nullable=True)
    shopify_variant_ids = Column(JSON, nullable=True)
    shopify_inventory_item_ids = Column(JSON, nullable=True)   # ✅ NEW — CRITICAL
    shopify_handle = Column(String, nullable=True)
    shopify_status = Column(String, nullable=True)
    shopify_store_id = Column(Integer, ForeignKey("shopify_stores.id"), nullable=True)


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String)