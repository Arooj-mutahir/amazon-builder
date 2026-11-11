from app.database import SessionLocal
from app.models import ShopifyStore
from datetime import datetime, timezone

db = SessionLocal()
stores = db.query(ShopifyStore).all()

print(f"Total stores: {len(stores)}\n")
for s in stores:
    now = datetime.now(timezone.utc)
    print(f"Store: {s.shop_domain}")
    print(f"  Access token: {s.access_token[:30]}..." if s.access_token else "  Access token: NONE")
    print(f"  Refresh token: {s.refresh_token[:30]}..." if s.refresh_token else "  Refresh token: NONE")
    print(f"  Expires at: {s.expires_at}")
    print(f"  Expired: {s.expires_at <= now if s.expires_at else 'NO EXPIRY'}")
    print()