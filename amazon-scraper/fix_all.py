from app.database import SessionLocal
from app.models import ShopifyStore, Product

db = SessionLocal()
try:
    print('Updating Stores...')
    for s in db.query(ShopifyStore).all():
        s.default_extra_percent = 0.0
        s.default_tax_rate = 0.0
        s.default_markup = 0.0
        s.default_markup_type = 'fixed'
        s.default_stock_qty = 0
        print(f'Store #{s.id} updated to 0')

    print('Updating Products...')
    count = 0
    for p in db.query(Product).all():
        p.extra_percent = 0.0
        p.tax_rate = 0.0
        p.markup = 0.0
        p.markup_type = 'fixed'
        count += 1
    print(f'{count} Products updated to 0')

    db.commit()
    print('SUCCESS: Database is now clean!')
except Exception as e:
    print(f'Error: {e}')
    db.rollback()
finally:
    db.close()
