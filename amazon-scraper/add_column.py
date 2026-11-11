from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE products ADD COLUMN shopify_variant_ids JSON;'))
    conn.commit()
    print('✅ Column "shopify_variant_ids" added successfully!')