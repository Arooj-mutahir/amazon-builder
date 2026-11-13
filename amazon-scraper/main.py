import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ API Routes (Yeh pehle aayenge)
app.include_router(shopify_router, prefix="/api/shopify")

@app.get("/api/health")
def health_check():
    return {"status": "success", "message": "API is running!"}

# ✅ FRONTEND SERVING LOGIC
FRONTEND_BUILD_DIR = "dist" 

if os.path.exists(FRONTEND_BUILD_DIR):
    # Assets mount karein
    app.mount("/assets", StaticFiles(directory=f"{FRONTEND_BUILD_DIR}/assets"), name="assets")
    
    # Catch-all route (React Router ke liye)
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # API requests ko ignore karein
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return {"detail": "Not Found"}
        
        # Agar koi static file maangi hai (jaise favicon)
        file_path = os.path.join(FRONTEND_BUILD_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Baaki sab ke liye index.html bhejein
        return FileResponse(f"{FRONTEND_BUILD_DIR}/index.html")
else:
    print(f"⚠️ WARNING: '{FRONTEND_BUILD_DIR}' folder nahi mila. Frontend serve nahi hoga.")
    @app.get("/")
    def root():
        return {"status": "error", "message": "Frontend build missing. API is running."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)