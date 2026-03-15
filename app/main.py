from fastapi import FastAPI
from app.routers import auth, links
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import SessionLocal
from app.services.link_service import delete_expired_links, delete_unused_links
from app.core.config import settings

app = FastAPI(title="URL Shortener Service")

app.include_router(auth.router)
app.include_router(links.router)

@app.get("/")
def root():
    return {"message": "URL Shortener Service is running"}

def cleanup_job():
    db = SessionLocal()
    try:
        expired_count = delete_expired_links(db)
        unused_count = delete_unused_links(db, settings.UNUSED_LINK_DAYS)
        if expired_count or unused_count:
            print(f"Cleaned up {expired_count} expired and {unused_count} unused links")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(
    cleanup_job,
    trigger=IntervalTrigger(minutes=5),
    id="cleanup_links",
    replace_existing=True,
)
scheduler.start()