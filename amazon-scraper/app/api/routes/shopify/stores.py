from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ShopifyStore

router = APIRouter()

@router.get("/stores")
def get_connected_stores(db: Session = Depends(get_db)):
    stores = db.query(ShopifyStore).all()
    # Frontend ko sirf id aur shop_domain bhejenge
    return [{"id": s.id, "shop_domain": s.shop_domain} for s in stores]