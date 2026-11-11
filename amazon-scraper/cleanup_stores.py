from app.database import SessionLocal
from app.models import ShopifyStore
from datetime import datetime, timezone

db = SessionLocal()
now = datetime.now(timezone.utc)

print("=== Current stores ===")
for s in db.query(ShopifyStore).all():
    is_valid = s.expires_at is None or s.expires_at > now
    status = "✅ VALID" if is_valid else "❌ EXPIRED"
    print(f"  {status} | {s.shop_domain}")

print("\n=== Deleting invalid stores ===")
invalid = db.query(ShopifyStore).filter(
    (ShopifyStore.access_token.is_(None)) |
    ((ShopifyStore.expires_at.isnot(None)) & (ShopifyStore.expires_at <= now))
).all()

for s in invalid:
    print(f"  ❌ Deleting: {s.shop_domain}")
    db.delete(s)

# Explicitly delete the typo store
typo = db.query(ShopifyStore).filter(
    ShopifyStore.shop_domain == "test-store-ispraip.myshopify.com"
).first()
if typo:
    print(f"  ❌ Deleting typo: {typo.shop_domain}")
    db.delete(typo)

db.commit()
print("\n=== Remaining stores ===")
for s in db.query(ShopifyStore).all():
    is_valid = s.expires_at is None or s.expires_at > now
    status = "✅ VALID" if is_valid else "❌ EXPIRED"
    print(f"  {status} | {s.shop_domain}")