from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config import StudioSettings
from .export import export_approved_drafts
from .ingest import scan_media_directory
from .models import MediaAsset
from .store import ContentStore
from .thumbnails import ThumbnailService

PACKAGE_DIR = Path(__file__).parent


class CaptionUpdate(BaseModel):
    caption: str


def create_app(settings: StudioSettings | None = None, store: ContentStore | None = None) -> FastAPI:
    settings = settings or StudioSettings()
    store = store or ContentStore(settings.db_path)

    app = FastAPI(title="Rafa Content Studio", version="0.1.0")
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    thumbnails = ThumbnailService(settings.thumbnail_path)
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")
    app.mount("/thumbnails", StaticFiles(directory=str(settings.thumbnail_path)), name="thumbnails")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "settings": settings,
                "items": _dashboard_items(store, thumbnails),
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

    @app.post("/api/export/approved")
    def export_approved(format: str = "json") -> dict[str, str | int]:
        if format not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format must be json or csv")
        result = export_approved_drafts(
            store,
            settings.export_path / f"approved-drafts.{format}",
            format=format,  # type: ignore[arg-type]
        )
        return {"path": str(result.path), "count": result.count, "format": result.format}

    @app.get("/exports/approved.{format}")
    def download_approved_export(format: str) -> FileResponse:
        if format not in {"json", "csv"}:
            raise HTTPException(status_code=400, detail="format must be json or csv")
        result = export_approved_drafts(
            store,
            settings.export_path / f"approved-drafts.{format}",
            format=format,  # type: ignore[arg-type]
        )
        return FileResponse(result.path, filename=result.path.name)

    return app


def _dashboard_items(
    store: ContentStore,
    thumbnails: ThumbnailService,
) -> list[dict[str, str | int | float]]:
    items = store.list_assets_with_drafts()
    for item in items:
        asset = MediaAsset(
            id=str(item["asset_id"]),
            filename=str(item["filename"]),
            absolute_path=str(item["absolute_path"]),
            relative_path=str(item["relative_path"]),
            media_type=str(item["media_type"]),
            size_bytes=int(item["size_bytes"]),
            modified_at=0,
        )
        item["thumbnail_url"] = thumbnails.ensure_thumbnail(asset).relative_url
    return items


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
