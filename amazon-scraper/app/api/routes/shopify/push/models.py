from pydantic import BaseModel
from typing import Optional

class StoreSettings(BaseModel):
    shop_domain: str
    markup: float
    markup_type: str
    extra_percent: Optional[float] = 0.0
    tax_rate: Optional[float] = 0.0
    default_stock_qty: Optional[int] = 0
    shopify_location_id: Optional[str] = None