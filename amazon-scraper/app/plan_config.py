# app/plan_config.py
"""
Har feature ka access yahan se control hota hai.
Frontend bhi yehi logic mirror karta hai — isliye ek jagah change = sab jagah change.
"""

PLAN_LIMITS = {
    "basic": {
        "max_users": 1,
        "max_products": 100,
        "manual_sync": False,
        "auto_sync": False,
        "webhooks": False,
        "size_chart": False,
        "compare_at_price": False,
        "image_mapping": False,
        "extra_pricing": False,   # extra_percent, tax_rate
        "pricing_fields": ["default_markup", "default_markup_type"],
    },
    "advance": {
        "max_users": 5,
        "max_products": -1,       # unlimited
        "manual_sync": True,
        "auto_sync": True,
        "webhooks": True,
        "size_chart": True,
        "compare_at_price": True,
        "image_mapping": True,
        "extra_pricing": True,
        "pricing_fields": [
            "default_markup", "default_markup_type", "default_extra_percent",
            "default_tax_rate", "default_compare_price_markup",
        ],
    },
}


def get_plan_features(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["basic"])


def has_feature(store, feature: str) -> bool:
    """Store ka plan + expiry check karke feature access deta hai."""
    if not store:
        return False
    if store.plan_status != "active":
        return False
    return get_plan_features(store.plan).get(feature, False)


def get_plan_snapshot(store) -> dict:
    """Frontend ko bhejne ke liye — sirf flags, tokens nahi."""
    return {
        "plan": store.plan,
        "status": store.plan_status,
        "expires_at": store.plan_expires_at.isoformat() if store.plan_expires_at else None,
        "features": get_plan_features(store.plan),
    }