"""One-time migration: shopify_inventory_item_ids + store stock settings."""
from app.database import engine
from sqlalchemy import text, inspect


def column_exists(conn, table, column):
    insp = inspect(conn)
    return column in [c["name"] for c in insp.get_columns(table)]


def migrate():
    is_postgres = engine.dialect.name == "postgresql"
    json_type = "JSONB" if is_postgres else "JSON"
    
    print(f"🔧 Database: {engine.dialect.name}")
    print(f"   JSON type: {json_type}\n")

    with engine.begin() as conn:
        if not column_exists(conn, "products", "shopify_inventory_item_ids"):
            conn.execute(text(f"ALTER TABLE products ADD COLUMN shopify_inventory_item_ids {json_type}"))
            print("✅ products.shopify_inventory_item_ids added")
        else:
            print("ℹ️  products.shopify_inventory_item_ids already exists")

        if not column_exists(conn, "shopify_stores", "default_stock_qty"):
            conn.execute(text("ALTER TABLE shopify_stores ADD COLUMN default_stock_qty INTEGER DEFAULT 100"))
            print("✅ shopify_stores.default_stock_qty added")
        else:
            print("ℹ️  shopify_stores.default_stock_qty already exists")

        if not column_exists(conn, "shopify_stores", "shopify_location_id"):
            conn.execute(text("ALTER TABLE shopify_stores ADD COLUMN shopify_location_id VARCHAR"))
            print("✅ shopify_stores.shopify_location_id added")
        else:
            print("ℹ️  shopify_stores.shopify_location_id already exists")

    print("\n=== VERIFICATION ===")
    with engine.connect() as conn:
        insp = inspect(conn)
        p_cols = [c["name"] for c in insp.get_columns("products")]
        s_cols = [c["name"] for c in insp.get_columns("shopify_stores")]
        print(f"products.shopify_inventory_item_ids: {'✅' if 'shopify_inventory_item_ids' in p_cols else '❌'}")
        print(f"shopify_stores.default_stock_qty:    {'✅' if 'default_stock_qty' in s_cols else '❌'}")
        print(f"shopify_stores.shopify_location_id:  {'✅' if 'shopify_location_id' in s_cols else '❌'}")


if __name__ == "__main__":
    migrate()
    print("\n🎉 Migration complete")