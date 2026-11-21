# app/api/routes/shopify/push/delete.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Product

router = APIRouter()

@router.delete("/products/{product_id}")
async def delete_product(product_id: int, store_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(
        Product.id == product_id, 
        Product.shopify_store_id == store_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return {"success": True, "message": "Product deleted successfully"}