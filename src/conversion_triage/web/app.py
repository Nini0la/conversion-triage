from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from conversion_triage.web.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="conversion-triage")

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(router)
    return app


app = create_app()
