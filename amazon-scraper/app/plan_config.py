# app/plan_config.py
"""
Har feature ka access yahan se control hota hai.
Frontend bhi yehi logic mirror karta hai — isliye ek jagah change = sab jagah change.
"""

from datetime import datetime

PLAN_LIMITS = {
    "basic": {
        "max_users": 1,
        "max_products": 1000,       # 🔥 Basic limit
        "manual_sync": False,
        "auto_sync": False,
        "webhooks": False,
        "size_chart": False,
        "compare_at_price": False,
        "image_mapping": False,
        "extra_pricing": False,     # extra_percent, tax_rate
        "pricing_fields": ["default_markup", "default_markup_type"],
    },
    "advance": {
        "max_users": 5,
        "max_products": 10000,      # 🔥 Advance limit
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

# 🔥 NAYA: Trial limit (Basic plan ke features ke saath)
TRIAL_DAYS = 7


def get_plan_features(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["basic"])


def has_feature(store, feature: str) -> bool:
    """Store ka plan + expiry check karke feature access deta hai."""
    if not store:
        return False
    if store.plan_status != "active":
        return False
    return get_plan_features(store.plan).get(feature, False)


def is_trial_active(store) -> bool:
    """Check karo ki trial abhi bhi active hai ya nahi."""
    if not store or not store.trial_ends_at:
        return False
    return store.trial_ends_at > datetime.utcnow()


def get_days_left_in_trial(store) -> int:
    """Trial khatam hone mein kitne din baaki hain."""
    if not store or not store.trial_ends_at:
        return 0
    delta = store.trial_ends_at - datetime.utcnow()
    return max(0, delta.days)


def get_product_limit(store) -> int:
    """Plan ke hisaab se product limit return karo."""
    if not store:
        return PLAN_LIMITS["basic"]["max_products"]
    plan = (store.plan or "basic").lower()
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["basic"])["max_products"]


def get_plan_snapshot(store) -> dict:
    """Frontend ko bhejne ke liye — sirf flags, tokens nahi."""
    if not store:
        return {
            "plan": "basic",
            "status": "active",
            "expires_at": None,
            "features": PLAN_LIMITS["basic"],
            "trial_ends_at": None,
            "days_left_in_trial": 0,
            "product_count": 0,
            "product_limit": 1000,
            "is_trial_active": False,
        }

    return {
        "plan": (store.plan or "basic").lower(),
        "status": (store.plan_status or "active").lower(),
        "expires_at": store.plan_expires_at.isoformat() if store.plan_expires_at else None,
        "features": get_plan_features(store.plan),
        # 🔥 NAYA: Trial + Limit fields
        "trial_ends_at": store.trial_ends_at.isoformat() if store.trial_ends_at else None,
        "days_left_in_trial": get_days_left_in_trial(store),
        "product_count": store.product_count or 0,
        "product_limit": get_product_limit(store),
        "is_trial_active": is_trial_active(store),
    }