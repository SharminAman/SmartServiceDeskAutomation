import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal, engine
from app.models import AdminUser, AllowedValue, RequestRow, Rule, RuleKeyword, Setting, Template  # noqa: F401
from app.routers import admin, auth_routes, dashboard, requests
from app.seed import seed
from app.settings import ROOT

app = FastAPI(title="Request Desk", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_routes.router)
app.include_router(dashboard.router)
app.include_router(requests.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup() -> None:
    last_error: Exception | None = None
    for _ in range(30):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            last_error = None
            break
        except SQLAlchemyError as exc:
            last_error = exc
            time.sleep(1)
    if last_error is not None:
        raise last_error
    from app.db import Base

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


@app.get("/api/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"ok": True}


def resolve_static_dir() -> Path | None:
    configured = os.getenv("STATIC_DIR", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates.append(ROOT / "frontend" / "dist")
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


STATIC_DIR = resolve_static_dir()
if STATIC_DIR is not None:
    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    def _page(full_path: str) -> FileResponse:
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return _page("")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        return _page(full_path)
