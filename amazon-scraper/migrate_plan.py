# migrate_plan.py
"""
One-time migration script.
Run: python migrate_plan.py
"""
from sqlalchemy import text
from app.database import engine

COLUMNS = [
    ("plan", "VARCHAR NOT NULL DEFAULT 'basic'"),
    ("plan_status", "VARCHAR NOT NULL DEFAULT 'active'"),
    ("plan_expires_at", "TIMESTAMP NULL"),
    ("plan_started_at", "TIMESTAMP NULL DEFAULT NOW()"),
    ("auto_sync_enabled", "BOOLEAN DEFAULT FALSE"),
    ("default_compare_price_markup", "DOUBLE PRECISION DEFAULT 0.0"),
]


def column_exists(conn, table: str, column: str) -> bool:
    q = text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    )
    return conn.execute(q, {"t": table, "c": column}).first() is not None


def main():
    print("🔍 Checking shopify_stores columns...\n")
    with engine.begin() as conn:
        for col, definition in COLUMNS:
            if column_exists(conn, "shopify_stores", col):
                print(f"✅ {col} — already exists")
                continue
            print(f"➕ Adding {col}...")
            conn.execute(
                text(f"ALTER TABLE shopify_stores ADD COLUMN {col} {definition}")
            )
            print(f"   ✅ {col} added")

    print("\n📋 Final state:")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, shop_domain, plan, plan_status FROM shopify_stores")
        ).fetchall()
        for r in rows:
            print(f"   id={r[0]} | {r[1]} | plan={r[2]} | status={r[3]}")

    print("\n🎉 Migration complete! Ab backend restart karo.")


if __name__ == "__main__":
    main()