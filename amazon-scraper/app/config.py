# app/config.py (Aapke FastAPI/Shopify project ke liye)
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./test.db"

    # Security
    SECRET_KEY: str = "change_this_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Shopify
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_SCOPES: str = "read_products,write_products"
    SHOPIFY_APP_URL: str = "https://example.com"

    # ✅ Yeh keys aapki .env se aayengi
    SHOPIFY_REDIRECT_URI: str = ""
    SHOPIFY_API_VERSION: str = "2024-04"
    SHOPIFY_SHOP_URL: str = ""
    SHOPIFY_WEBHOOK_SECRET: str = ""
    ENVIRONMENT: str = "development"

    # ✅ OmkarCloud Scraper ka base URL
    OMKARCLOUD_URL: str = "http://localhost:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()