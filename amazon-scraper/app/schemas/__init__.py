# ============================================
# app/schemas/__init__.py
# ============================================

from pydantic import BaseModel

# Admin Login ke liye
class AdminLogin(BaseModel):
    username: str
    password: str

# Token response ke liye
class Token(BaseModel):
    access_token: str
    token_type: str