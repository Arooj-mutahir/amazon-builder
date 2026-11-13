import uvicorn
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from urllib.parse import urlencode

# ✅ Router import
from app.api.routes.shopify import router as shopify_router
from app.database import engine, Base
from app import models 
from app.services.scheduler import start_scheduler, scheduler

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    scheduler.shutdown()

app = FastAPI(title="Amazon to Shopify Scraper", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Sirf yahan prefix lagayein
app.include_router(shopify_router, prefix="/api/shopify")

@app.get("/")
def read_root(request: Request):
    # ✅ If Shopify opens the app (has hmac or host param), serve the React app
    if "hmac" in request.query_params or "host" in request.query_params:
        
        # ✅ FIX: Sirf shop aur host bhejein, hmac aur id_token nahi
        params = {}
        if "shop" in request.query_params:
            params["shop"] = request.query_params["shop"]
        if "host" in request.query_params:
            params["host"] = request.query_params["host"]
            
        qs = urlencode(params)
        frontend_url = "https://ingenious-caring-production-c9aed584.up.railway.app"
        redirect_target = f"{frontend_url}?{qs}" if qs else frontend_url
        
        # 🚨 302 lagana zaroori hai taaki white screen na aaye
        return RedirectResponse(url=redirect_target, status_code=302)
    
    return {"status": "success", "message": "Scraper & Shopify Server is running!"}

# Agar static folder nahi hai toh yeh error nahi dega
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # Note: Uvicorn ko normally "app.main:app" se run karte hain
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)