from fastapi import APIRouter, BackgroundTasks
from app.services.scheduler import run_price_update_now

router = APIRouter()

@router.post("/sync-prices")
async def sync_prices_manually(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_price_update_now)
    return {"success": True, "message": "Price + stock sync started in background. Check terminal!"}