from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS list_price float8;"))
    conn.commit()

print("✅ list_price column added successfully!")