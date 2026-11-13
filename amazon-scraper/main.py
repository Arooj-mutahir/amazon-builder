import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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
    allow_origins=["*"], # Ya specific Vercel URL dalein
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ API Routes
app.include_router(shopify_router, prefix="/api/shopify")

@app.get("/api/health")
def health_check():
    return {"status": "success", "message": "API is running!"}

@app.get("/")
def read_root():
    return {"status": "success", "message": "Backend API is running perfectly!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)