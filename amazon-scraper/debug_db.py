from app.database import SessionLocal
from app.models import ShopifyStore, Product

db = SessionLocal()
try:
    print('=== STORES ===')
    for s in db.query(ShopifyStore).all():
        print(f'Store #{s.id} | Domain: {s.shop_domain}')
        print(f'   Markup: {s.default_markup} | Type: {s.default_markup_type}')
        print(f'   Extra: {s.default_extra_percent}  <-- YEH CHECK KAREIN')
        print(f'   Tax: {s.default_tax_rate} | Stock: {s.default_stock_qty}')
    print()
    print('=== PRODUCTS (First 10) ===')
    for p in db.query(Product).limit(10).all():
        print(f'ASIN {p.asin} | Extra: {p.extra_percent} | Markup: {p.markup} | Type: {p.markup_type}')
finally:
    db.close()
