import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from database import engine
import models
from routers import auth, dashboard, cases, actions, people, notifications, reports, calendar, admin
from seed import seed
from templates_config import templates

models.Base.metadata.create_all(bind=engine)
seed()

app = FastAPI(title="Legal Case Management System", version="1.0.0")
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(cases.router)
app.include_router(actions.router)
app.include_router(people.router)
app.include_router(notifications.router)
app.include_router(reports.router)
app.include_router(calendar.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
