import asyncio
from app.worker.sync_job import sync_prices_job

if __name__ == "__main__":
    print("🚀 Manually running Sync Job...")
    asyncio.run(sync_prices_job())
    print("✅ Sync Job Finished!")