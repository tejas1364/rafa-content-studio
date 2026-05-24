from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config import StudioSettings
from .ingest import scan_media_directory
from .store import ContentStore

PACKAGE_DIR = Path(__file__).parent


class CaptionUpdate(BaseModel):
    caption: str


def create_app(settings: StudioSettings | None = None, store: ContentStore | None = None) -> FastAPI:
    settings = settings or StudioSettings()
    store = store or ContentStore(settings.db_path)

    app = FastAPI(title="Rafa Content Studio", version="0.1.0")
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "settings": settings,
                "items": store.list_assets_with_drafts(),
            },
        )

    @app.post("/api/scan")
    def scan() -> dict[str, int | str]:
        assets = scan_media_directory(settings.media_path)
        imported = store.upsert_assets(assets)
        return {"assets_imported": imported, "media_dir": str(settings.media_path)}

    @app.post("/api/drafts/{draft_id}/approve")
    def approve_draft(draft_id: str) -> dict[str, str]:
        return _draft_to_response(store, draft_id, "approved")

    @app.post("/api/drafts/{draft_id}/reject")
    def reject_draft(draft_id: str) -> dict[str, str]:
        return _draft_to_response(store, draft_id, "rejected")

    @app.post("/api/drafts/{draft_id}/caption")
    def update_caption(draft_id: str, update: CaptionUpdate) -> dict[str, str]:
        try:
            draft = store.set_caption(draft_id, update.caption)
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=404 if isinstance(error, KeyError) else 400, detail=str(error))
        return {
            "id": draft.id,
            "asset_id": draft.asset_id,
            "caption": draft.caption,
            "status": draft.status,
        }

    return app


def _draft_to_response(store: ContentStore, draft_id: str, status: str) -> dict[str, str]:
    try:
        draft = store.set_draft_status(draft_id, status)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error))
    return {
        "id": draft.id,
        "asset_id": draft.asset_id,
        "caption": draft.caption,
        "status": draft.status,
    }


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    return create_app()


app = get_app()
